/**
 * @file visual.cc
 * @author Yi-Mu Chen
 * @brief Implementation of the visual interface.
 *
 * @class Visual
 * @ingroup hardware
 * @brief Visual system interface class
 *
 * As the visual process has a long startup time, a thread will be started
 * whenever a visual system is declared, which will constantly flush the
 * contents of the camera interface to a buffer, process the standardized image
 * processing routine, and store the processed image and extracted variables,
 * and repeat until some termination code is received. This looped thread will
 * be briefly paused when the user request the image, to ensure the integrity
 * of the transferred data. The core of the image processing functions is
 * photo-detector finding: finding the optimal "dark rectangle" within the
 * image, and calculated in the center of this rectangle in terms of pixel
 * coordinates.
 *
 * This will be the one interface functions that does not start use a singleton
 * notation, as the system can potentially have more than 1 camera running
 * similar algorithms.
 *
 * ## Visual processing thread management.
 *
 * There are 3 data members in the Visual class used for managing the thread.
 * - std::thread loop_thead: the thread object for handling the loop function
 * - std::atomic<bool> run_loop: the thread-safe flag variable to indicate
 *   whether the loop should continue.
 * - std::mutex loop_mutex: Mutex lock required for data manipulation of the
 *   image containers.
 *
 * The main loop will basically loop over the following:
 * - Check if run_loop is true. Exit the loop if not.
 * - Wait to lock the mutex.
 * - Extract image and perform image processes
 * - unlock the mutex.
 * - Wait a fixed pause period.
 *
 * Under this model, the image extraction functions has windows in which it can
 * choose to lock the mutex while it perform data extraction. The starting and
 * stopping of the loop is also a simple check on the value of the `run_loop`
 * variable.
 *
 * ## Visual processing algorithm for finding a photo detecting element
 *
 * The algorithm uses as much inbuilt OpenCV functions as possible to avoid
 * being over taxing on the lowe power processing system the calibration stand
 * is expected to run on. The algorithm is as follows:
 *
 * - Convert the image into a binary image by some grayscale threshold value.
 * - Use the binary image to generate a contours of the high-contrast features
 *   in the image.
 * - For the found contours, the following filters is applied:
 *   - The size (bounding box area), must be greater than some value (this
 *     removes noise speckles).
 *   - The ratio of the edges of the bounding box must be sufficiently similar
 *     (the photo detecting element is expected to be square.)
 *   - The internal area of the original image within the contour must be
 *     sufficiently dark (as photo-detecting elements are expected to be gray)
 *   - The convex hull of the contour must be able to be approximated as a
 *     rectangle.
 * - The convex hull of the remaining contours will be used. The use of convex
 *   hulls is to eliminate reflection artifacts that might appear on the
 *   detector face.
 * - The convex hull with the largest area will be assumed to be the detector
 *   element of interest, then the following parameters will be determined and
 *   stored in the VisualResults class:
 *   - The average pixel position of the convex hull in (x,y)
 *   - The pixel position of the convex hull after polygon approximation
 *   - The sharpness measure of the surrounding image.
 *
 * Functions should beable to receive a cv::Mat object as the input, to allow
 * for arbitrary levels of debugging and feature demonstration.
 */
#include "logger.hpp"
#include "visual.hpp"
#include <fmt/printf.h>
#include <opencv2/core/utils/logger.hpp>

// Helper objects for consistant display (format BGR)
static const cv::Scalar red( 100, 100, 255 );
static const cv::Scalar cyan( 255, 255, 100 );
static const cv::Scalar yellow( 100, 255, 255 );
static const cv::Scalar blue( 255, 100, 100 );
static const cv::Scalar green( 100, 255, 100 );
static const cv::Scalar white( 255, 255, 255 );

// Setting OPENCV into silent mode
static const auto __dummy_settings = cv::utils::logging::setLogLevel(
  cv::utils::logging::LOG_LEVEL_SILENT );

// Python logging options

Visual::Visual() : cam (),
  run_loop             ( false )
{
  InitVarDefault();
  StartLoopThread();
}


Visual::Visual( const std::string& dev ) : cam (),
  run_loop                                     ( false )
{
  init_dev( dev );
  InitVarDefault();
  StartLoopThread();
}


std::string
Visual::DeviceName() const
{
  return "Visual@"+dev_path;
}


/**
 * @brief Starting the visual instance at the some device path.
 *
 * The device path on a unix machine will typically be something like:
 * `/dev/video0`, input whatever camera device is used for the system. Notice
 * that the camera device would need to be covered by the v462 Linux video
 * device drivers to function properly on the real system.
 *
 * In addition: we will ensure the following settings on the camera device:
 * - Fix the resolution as 1280x1024. This ensures that the visual processing
 *   algorithm will perform in realtime
 * - Reduce the buffer to 0. This ensures that the image received from the
 *   camera will be as close to real time as possible.
 * - Switch **off** any known image processing. This is so that image
 *   processing artifacts does not skew the image processing algorithms we use.
 *
 * A thread will be started as soon as the devices is known to be available.
 */
void
Visual::init_dev( const std::string& dev )
{
  EndLoopThread();
  dev_path = dev;
  cam.release();
  cam.open( dev_path );
  if( !cam.isOpened() ){// check if we succeeded
    throw device_exception( DeviceName(), "Cannot open webcam" );
  }

  // Additional camera settings
  cam.set( cv::CAP_PROP_FRAME_WIDTH,  1280 );
  cam.set( cv::CAP_PROP_FRAME_HEIGHT, 1024 );
  cam.set( cv::CAP_PROP_BUFFERSIZE,   1 );// Reducing buffer for fast capture
  cam.set( cv::CAP_PROP_SHARPNESS,    0 );// disable post-process sharpening.
  StartLoopThread();
}


Visual::~Visual()
{
  printdebug( DeviceName(), "Ending the visual thread" );
  EndLoopThread();
  printdebug( DeviceName(), "Closing visual system interfaces" );
  cam.release();
  printdebug( DeviceName(), "Visual interface closed" );
}


unsigned
Visual::FrameWidth() const
{
  return cam.get( cv::CAP_PROP_FRAME_WIDTH );
}


unsigned
Visual::FrameHeight() const
{
  return cam.get( cv::CAP_PROP_FRAME_HEIGHT );
}


/********************************************************************************
 *
 * THREAD MANAGEMENT FUNCTIONS
 *
 *******************************************************************************/


/**
 * @brief The method used for running the loop.
 *
 * The atomic object needs to be passed in as a argument to function properly.
 * In between loop iterations, a fixed 5 millisecond paused is used to ensure
 * that other processes has a chance to extract image and processing results
 * when requested. This pause must be faster than the camera
 * refresh rate to have a real-time like iamge presentation in the GUI program.
 */
void
Visual::RunMainLoop( std::atomic<bool>& run_loop )
{
  namespace st = std::chrono;
  auto get_time = []( void )->size_t {
                    return st::duration_cast<st::microseconds>(
                      st::high_resolution_clock::now().time_since_epoch()).count();
                  };
  while( run_loop == true ){
    const size_t time_start = get_time();
    size_t       time_end   = get_time();
    loop_mutex.lock();

    do{
      cam >> image;
    } while( ( image.empty() || image.cols == 0 ) && cam.isOpened() );

    latest = FindDetector( image );
    loop_mutex.unlock();

    while( time_end-time_start < 5e3 ){
      std::this_thread::sleep_for( st::milliseconds( 1 ) );
      time_end = get_time();
    }
  }
}


/**
 * @brief Starting the loop thread.
 */
void
Visual::StartLoopThread()
{
  run_loop    = true;
  loop_thread = std::thread( [this]{
    this->RunMainLoop( std::ref( run_loop ) );
  } );
}


/**
 * @brief Setting the loop to stop and waiting for the thread to terminate.
 */
void
Visual::EndLoopThread()
{
  if( run_loop == true ){
    run_loop = false;
    loop_thread.join();
  }
}


/**
 * @brief Extraction of the visual processing results.
 */
Visual::VisResult
Visual::GetVisResult()
{
  loop_mutex.lock();
  VisResult ans = latest;
  loop_mutex.unlock();
  return ans;
}


/**
 * @brief Extraction of the image, either the raw unprocessed image, or the
 * descriptive image which includes the processed contours.
 *
 * In the rare event that the frame is empty (either because the camera was
 * never properly initialized, or that there was an issue with the image
 * transfer process), a blank (all 0 value image) with the correct dimensions
 * will be returned to ensure that all subsequent functions will function
 * nominally.
 */
cv::Mat
Visual::GetImage( const bool raw )
{
  static const cv::Mat blank_frame( cv::Size( FrameWidth(), FrameHeight() ),
                                    CV_8UC3, cv::Scalar( 0, 0, 0 ) );
  loop_mutex.lock();
  cv::Mat ans_mat =
    ( display.empty() ||
      display.cols == 0 ) ? blank_frame : raw ? image : display;
  loop_mutex.unlock();
  return ans_mat;
}


/**
 * @brief Saving the image to some path.
 */
bool
Visual::SaveImage( const std::string& path, bool raw )
{
  const cv::Mat mat = GetImage( raw );
  cv::imwrite( path, mat );
  return true;
}


/**
 * @brief Returning the image as a JPEG encoded string.
 *
 * This method is required by the GUI interface to allow for streaming of data
 * via HTTP image requests.
 */
std::vector<uchar>
Visual::GetImageBytes()
{
  std::vector<uchar> buf;// Storage required by opencv.
  const auto         img = GetImage( false );
  if( img.empty() ){
    throw device_exception( DeviceName(), "Image empty" );
  }
  cv::imencode( ".jpg", img, buf );
  return buf;
}


/********************************************************************************
 *
 * VISUAL PROCESSING ALGORITHM
 *
 *******************************************************************************/

/**
 * @brief Default settings values of the algorithm
 *
 * Last determined 2021.05.31.
 */
void
Visual::InitVarDefault()
{
  threshold    = 80;
  blur_range   = 5;
  lumi_cutoff  = 40;
  size_cutoff  = 50;
  ratio_cutoff = 1.4;
  poly_range   = 0.08;
}


/**
 * @brief Given image in cv::Mat format. Compute the visual algorithm results
 * and stored in a processed version of the image in the internal buffer.
 *
 * This handles the main control flow of:
 * - Extracting the image.
 * - Running the contouring algorithm
 * - Morphing the results into the standard VisResult format.
 */
Visual::VisResult
Visual::FindDetector( const cv::Mat& img )
{
  static const VisResult empty_return =
    VisResult { -1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };

  // Early exits if image is not found.
  if( img.empty() || img.cols == 0 ){
    return empty_return;
  }
  const auto  contours = FindContours( img );
  const auto& hulls    = contours.at( 0 );
  const auto  ans      = hulls.empty() ? empty_return : MakeResult( img,
                                                                    hulls.at(
                                                                      0 ) );
  display = MakeDisplay( img, contours );
  return ans;
}


/**
 * @brief Given an base image, find the contours and group them according to
 * the various selection criteria.
 *
 * Storing outputs of the opencv contouring algorithm according to where they
 * pass the selection:
 * - If they fail the minimal size requirements, these contours are discarded
 *   as these are typically imaging "speckles" that comes from image sensor
 *   noise.
 * - All other selection criteria (rectangular approximation, luminosity
 *   requirements, size requirements... etc) should always be store, as failed
 *   contours is a good indication for which parameters need to be tuned for
 *   when the algorithm apparently fails.
 */
std::vector<Visual::ContourList>
Visual::FindContours( const cv::Mat& img ) const
{
  const ContourList contours = GetRawContours( img );
  ContourList       failed_ratio;
  ContourList       failed_lumi;
  ContourList       failed_rect;
  ContourList       hulls;

  // Calculating all contour properties
  for( const auto& cont : contours ){
    const double size = GetContourSize( cont );
    if( size < size_cutoff ){
      continue;
    }
    const cv::Rect bound = cv::boundingRect( cont );
    const double   ratio = (double)bound.height / (double)bound.width;
    if( ratio > ratio_cutoff || ratio < 1. / ratio_cutoff ){
      failed_ratio.push_back( cont );
      continue;
    }
    const double lumi = GetImageLumi( img, cont );
    if( lumi > lumi_cutoff ){
      failed_lumi.push_back( cont );
      continue;
    }
    const Contour_t hull = GetConvexHull( cont );
    const Contour_t poly = GetPolyApprox( hull );
    if( poly.size() != 4 ){
      failed_rect.push_back( cont );
      continue;
    }
    hulls.push_back( hull );
  }
  std::sort( hulls.begin(), hulls.end(), Visual::CompareContourSize );
  return { hulls, failed_rect, failed_lumi, failed_ratio };
}


/**
 * @brief Given the original image in cv::Mat format, and the candidate convex
 * contour, calculate the summary results.
 *
 * The summary results include:
 * - The average position in pixels in the area covered by the contour.
 * - The sharpness measure (2nd and 4th order), calculated in a bounding
 *   rectangle twice the size of the original bounding rectangle.
 * - The area (in pixels) of the convex hull
 * - The maximum distance fo two points in the contour
 * - The 8 coordinates of the corners after polygon approximation.
 */
Visual::VisResult
Visual::MakeResult( const cv::Mat& img, const Visual::Contour_t& hull ) const
{
  // position calculation of final contour
  const cv::Moments m = cv::moments( hull, false );

  // Maximum distance in contour
  const double    distmax      = GetContourMaxMeasure( hull );
  const Contour_t poly         = GetPolyApprox( hull );
  const cv::Rect  bound        = cv::boundingRect( hull );
  const cv::Rect  double_bound = cv::Rect( bound.x-bound.width / 2,
                                           bound.y-bound.height / 2,
                                           bound.width * 2, bound.height * 2 );
  const auto p = sharpness( img, double_bound );
  return VisResult {m.m10 / m.m00, m.m01 / m.m00, p.second, p.first, m.m00,
                    distmax, poly.at( 0 ).x, poly.at( 1 ).x, poly.at( 2 ).x,
                    poly.at( 3 ).x,
                    poly.at( 0 ).y, poly.at( 1 ).y, poly.at( 2 ).y,
                    poly.at( 3 ).y, };
}


/**
 * @brief Given the original image in cv::Mat format, and the sorted list of
 * contours found, generate a processed image with contours.
 *
 * Each different fail mode displayed in a different color for debugging simple
 * debugging. The return is the processed image in a standard opencv::Mat data
 * format.
 */
cv::Mat
Visual::MakeDisplay( const cv::Mat&                          img,
                     const std::vector<Visual::ContourList>& contlist ) const
{
  // Drawing variables
  char    msg[1024];
  cv::Mat ret             = img.clone();
  auto    PlotContourList =
    [this, &ret]( const Visual::ContourList& list,
                  const cv::Scalar& color )->void {
      for( unsigned i = 0; i < list.size(); ++i ){
        cv::drawContours( ret, list, i, color );
      }
    };
  auto PlotText =
    [this, &ret]( const std::string& str, const cv::Point& pos,
                  const cv::Scalar& col )->void {
      cv::putText( ret, str, pos, cv::FONT_HERSHEY_SIMPLEX, 0.8,
                   col, 2 );
    };
  PlotContourList( contlist.at( 0 ), cyan   );
  PlotContourList( contlist.at( 1 ), white );
  PlotContourList( contlist.at( 2 ), green );
  PlotContourList( contlist.at( 3 ), yellow );

  // Plotting the final results
  if( contlist.at( 0 ).empty() ){
    PlotText( "NOT FOUND", cv::Point( 20, 20 ), red );
  } else {
    const auto   res = MakeResult( img, contlist.at( 0 ).at( 0 ) );
    const double x   = res.x;
    const double y   = res.y;
    const double s2  = res.sharpness_m2;
    const double s4  = res.sharpness_m4;
    sprintf( msg, "x:%.1lf y:%.1lf s2:%.2lf s4:%.2lf", x, y, s2, s4 );
    cv::drawContours( ret, contlist.at( 0 ), 0, red, 3 );
    cv::circle( ret, cv::Point( x, y ), 3, red, cv::FILLED );
    PlotText( msg, cv::Point( 20, 20 ), red );
  } return ret;
}


/**
 * @brief The threshold-and-contour algorithm.
 *
 * An extra blur is applied to the gray-scaled image to avoid noise speckles
 * from affecting the sharpness measure.
 */
std::vector<Visual::Contour_t>
Visual::GetRawContours( const cv::Mat& img ) const
{
  cv::Mat                gray_img;
  std::vector<cv::Vec4i> hierarchy;
  std::vector<Contour_t> contours;

  // Standard image processing.
  cv::cvtColor( img, gray_img, cv::COLOR_BGR2GRAY );
  cv::blur( gray_img, gray_img, cv::Size( blur_range, blur_range ) );
  cv::threshold( gray_img, gray_img, threshold, 255, cv::THRESH_BINARY );
  cv::findContours( gray_img, contours, hierarchy, cv::RETR_TREE,
                    cv::CHAIN_APPROX_SIMPLE, cv::Point( 0, 0 ) );
  return contours;
}


/**
 * @brief Given the the original image and a contour of interest, computed the
 * luminosity of the internal area.
 *
 * Here we use the conversion to luminosity using the formula found here:
 * https://en.wikipedia.org/wiki/Relative_luminance
 */
double
Visual::GetImageLumi( const cv::Mat& img, const Contour_t& cont ) const
{
  // Expecting the internals of the photosensor to be dark.
  const std::vector<Contour_t> v_cont = { cont };
  cv::Mat                      mask   = cv::Mat::zeros( img.size(), CV_8UC1 );
  cv::drawContours( mask, v_cont, 0, 255, cv::FILLED );
  const cv::Scalar meancol = cv::mean( img, mask );
  return 0.2126 * meancol[0]+0.7152 * meancol[1]+0.0722 * meancol[2];
}


/**
 * @brief Comparison of contour size (bounding box area)
 */
bool
Visual::CompareContourSize( const Contour_t& x, const Contour_t& y )
{
  const cv::Rect x_bound = cv::boundingRect( x );
  const cv::Rect y_bound = cv::boundingRect( y );
  return x_bound.area() > y_bound.area();
}


/**
 * @brief Abstraction for computing the convex hull.
 */
Visual::Contour_t
Visual::GetConvexHull( const Contour_t& x ) const
{
  Contour_t hull;
  cv::convexHull( cv::Mat( x ), hull );
  return hull;
}


/**
 * @brief Abstraction for getting a polygon approximation.
 */
Visual::Contour_t
Visual::GetPolyApprox( const Contour_t& x ) const
{
  Contour_t    ans;
  const double size = GetContourSize( x );
  cv::approxPolyDP( x, ans, size * poly_range, true );
  return ans;
}


/**
 * @brief Getting the maximum measure of the contour (largest of the x/y
 * measure)
 */
double
Visual::GetContourSize( const Contour_t& x ) const
{
  const cv::Rect bound = cv::boundingRect( x );
  return std::max( bound.height, bound.width );
}


/**
 * @brief Getting the maximum distance of two points within a contour.
 */
double
Visual::GetContourMaxMeasure( const Contour_t& x ) const
{
  // Maximum distance in contour
  double ans = 0;
  for( const auto& p1 : x ){
    for( const auto& p2 : x ){
      ans = std::max( ans, cv::norm( p2-p1 ) );
    }
  }
  return ans;
}


/**
 * @brief Given the original image and a rectangular region of interest,
 * compute the sharpness measure.
 *
 * The sharpness measure is defined by taking the gray-scaled image apply a
 * small blur, then compute the laplace transformed image. Then taking the
 * standard deviation (2nd order variance) and Kurtosis measure (4th order
 * variance) of the transformed image.
 */
std::pair<double, double>
Visual::sharpness( const cv::Mat& img, const cv::Rect& crop ) const
{
  // Image containers
  cv::Mat cimg[3], bimg, fimg, lap;

  // Variable containers
  cv::Scalar mu, sigma;

  // Convert original image to gray scale
  cv::cvtColor( img, bimg, cv::COLOR_BGR2GRAY );

  // Getting green channel image image converting to gray scale
  // cv::split( img, // cimg );
  // cimg[1].convertTo( fimg, CV_32FC1 );
  // Creating the crops
  if( crop.width == 0 || crop.height == 0 ){
    return std::pair<double, double>( 0, 0 );
  }

  // Cropping to range sometimes is bad... not sure why just yet
  try {bimg = bimg( crop ).clone();
  } catch( cv::Exception& e ){
    return std::pair<double, double>( 0, 0 );
  }
  cv::blur( bimg, bimg, cv::Size( 2, 2 ) );

  // Calculating lagrangian
  cv::Laplacian( bimg, lap, CV_64F, 5 );

  // Calculating the 2nd and 4th moment
  mu = cv::mean( lap );
  double mo2 = 0, mo4 = 0;
  for( int r = 0; r < lap.rows; ++r ){
    for( int c = 0; c < lap.cols; ++c ){
      const double val  = lap.at<double>( r, c );
      const double diff = val-mu.val[0];
      mo2 += diff * diff;
      mo4 += diff * diff * diff * diff;
    }
  }
  mo2 /= lap.rows * lap.cols;
  mo4 /= lap.rows * lap.cols;
  return std::pair<double, double>( mo4 / ( mo2 * mo2 ), mo2 );
}
