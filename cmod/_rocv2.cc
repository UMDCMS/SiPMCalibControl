/**
 * @file _rocv2.cc
 * @author Yi-Mu "Enoch" Chen
 * @date 2023-07-28
 * @brief Exposing the HGCROCv2 Raw data formats as a numpy/awkward friendly
 * fields. Attempting to keep everything in a single file.
 */

#include <boost/archive/binary_iarchive.hpp>
#include <boost/crc.hpp>

#include <bitset>
#include <fstream>
#include <iostream>
#include <numeric>

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "HGCROCv2RawData.h"

/**
 * @brief Container for the HGCROCv2 data value arrays
 *
 * @details The HGCROCv2 raw data format contains has the following fields:
 *
 * - Per event values: uniquely 1 value per event:
 *   - event: the index for the event values
 *   - chip: The chip ID of the HGROC. Supposedly this should be a file-wide
 *     variable, but we don't have  so much
 *   - trigger time
 *   - trigger width
 *
 * - Per half values: each event will attempt to readout the results of up to 2
 *   HGCROC halves.
 *   - corruption
 *   - bxcounter
 *   - eventcounter
 *   - orbitcounter
 *
 * - Per channel values: each event, every readout channel will have their
 *   readout information stored as well as some identification.
 *   - half: which HGCROC half the channel belongs to.
 *   - channel: the channel we are attempting to read out
 *   - adc: readout value (bits)
 *   - adcm:
 *   - toa: Time of arrival
 *   - tot: Time over threshold
 *   - totflag: results of the initial flag result
 *
 * - Trigger link values: for each event, each active trigger link will store 4
 *   sets of trigger information
 *   - validtp: True/False flag for whether this trigger was valid.
 *   - channelsumid
 *   - rawsum
 *   - decompression sum.
 *
 * We pull the information of HGCROCv2RAWData format stored in a .raw file, and
 * process it into an intermediate, easy-to-understand format that is also
 * friendly to numpy/awkward arrays for the python-level data analysis used for
 * the online data processing.
 *
 * All data arrays will be stored as 1-D arrays, the folding of array structures
 * will be handled by python/numpy/awkward.
 */
class rocv2
{
public:
  /**
   * @brief Constructing the data arrays from a raw data file.
   *
   * HGCROCv2RawData is compatible with boost::serialization functions. Based on
   * the unpack method [1].
   *
   * [1]
   * https://gitlab.cern.ch/hgcal-daq-sw/hexactrl-sw/-/blob/ROCv3/sources/client/executables/unpack.cxx#L74
   */
  rocv2( const std::string& raw_file )
  {
    // Starting the folding structure methods.
    this->nhalves   = 0;
    this->nchannels = 0;
    this->nlinks    = 0;

    std::ifstream                   infile( raw_file );
    boost::archive::binary_iarchive ia( infile );
    HGCROCv2RawData                 roc_buffer;

    while( 1 ){
      try{
        ia >> roc_buffer;
        this->extend( roc_buffer );
      } catch( std::exception& e ){
        break;
      }
    }
  }


  // Defining all arrays as 1D arrays (with std::vector) with a automatic
  // casting to python arrays.
#define DEFINE_ARRAY( arr_name, type ) \
  std::vector<type> _ ## arr_name;     \
  inline pybind11::array_t<type>       \
  arr_name() const {return vector_to_array<type>( this->_ ## arr_name );}

  DEFINE_ARRAY( event, uint32_t );
  DEFINE_ARRAY( chip, uint32_t );
  DEFINE_ARRAY( trigtime, uint32_t );
  DEFINE_ARRAY( trigwidth, uint32_t );


  // Per half entry (2-per instance)
  uint8_t nhalves; // Defined in data file.
  DEFINE_ARRAY( corruption, uint32_t );
  DEFINE_ARRAY( bxcounter, uint16_t );
  DEFINE_ARRAY( eventcounter, uint8_t );
  DEFINE_ARRAY( orbitcounter, uint8_t );

  // Per readout channel entry (2x24 entries per instance)
  uint8_t nchannels;
  DEFINE_ARRAY( half, uint8_t );
  DEFINE_ARRAY( channel, uint8_t );
  DEFINE_ARRAY( adc, uint16_t );
  DEFINE_ARRAY( adcm, uint16_t );
  DEFINE_ARRAY( toa, uint16_t );
  DEFINE_ARRAY( tot, uint16_t );
  DEFINE_ARRAY( totflag, uint8_t );


  // Per trigger channel entry (4 per instance)
  uint8_t nlinks;
  DEFINE_ARRAY( validtp, uint8_t );
  DEFINE_ARRAY( channelsumid, uint8_t );
  DEFINE_ARRAY( rawsum, uint8_t );
  DEFINE_ARRAY( decompresssum, uint32_t );
#undef DEFINE_ARRAY

private:
  /****************************************************************************/
  /* Helper method for checking data formatting information                   */
  /****************************************************************************/

  uint8_t
  get_nhalves( const HGCROCv2RawData& raw_data ) const
  {
    const uint8_t new_n = raw_data.data().size() >=
                          ( 2 * HGCROC_DATA_BUF_SIZE ) ? 2 : 1;
    if( this->nhalves == 0 || this->nhalves == new_n ){
      return new_n;
    } else {
      throw std::runtime_error( "Mismatch number of halves" );
      return 0;
    }
  }


  uint8_t
  get_nlinks( const HGCROCv2RawData& raw_data ) const
  {
    const uint8_t new_n = raw_data.data().size()
                          -( HGCROC_DATA_BUF_SIZE * this->nhalves );
    if( this->nlinks == 0 || this->nlinks == new_n ){
      return new_n;
    } else {
      throw std::runtime_error( "Mismatch number of links!" );
      return 0;
    }
  }


  static const uint8_t N_READOUT_CHANNELS = 38; // Fixed value for now

  uint8_t
  get_nchannels( const HGCROCv2RawData& rawdata ) const
  {
    return rocv2::N_READOUT_CHANNELS+1;
  }


  /******************************************************************************/
  /* Static helper function for parsing data into simpler format.               */
  /* Parsing of the data words into the relevant data is based on the functions */
  /* found here:                                                                */
  /* https://gitlab.cern.ch/hgcal-daq-sw/hexactrl-sw/-/blob/ROCv3/sources/client/src/ntupler.cc#L131 */
  /******************************************************************************/

  inline static int
  get_trigger_offset( const HGCROCv2RawData& roc_data )
  {
    int offset = -1;
    int index  = 0;
    for( auto latency : roc_data.triglatency() ){
      if( latency != 0 ){
        for( auto i = 0; i < 32; i++ ){
          if( ( ( latency >> ( 31-i )) & 0x1 ) == 1 ){
            offset = 32 * index+i;
            break;
          }
        }
        if( offset >= 0 ){break;}
      } else {
        index++;
      }
    }
    return offset;
  }


  inline static int
  get_trigwidth( const HGCROCv2RawData& roc_data )
  {
    return std::accumulate(
      roc_data.triglatency().begin(),
      roc_data.triglatency().end(),
      0, [&]( uint32_t width, const uint32_t val ){
      return width+std::bitset<32>( val ).count();
    } );
  }


  inline static uint16_t
  get_bxcounter( const uint32_t header )
  {
    return ( header >> 16 ) & 0xfff;
  }


  inline static uint8_t
  get_eventcounter( const uint32_t header )
  {
    return ( header & 0xffff ) >> 10;
  }


  inline static uint8_t
  get_orbitcounter( const uint32_t header )
  {
    return ( header & 0x3ff ) >> 7;
  }


  static int
  get_corruption( const std::vector<uint32_t>& data )
  {
    const uint32_t head = ( data[0] >> 28 ) & 0xf;
    const uint32_t tail = ( data[0] ) & 0xf;

    // Getting the Cyclic redundancy code
    std::vector<uint32_t> crcvec( data.begin(), data.end());

    std::transform( crcvec.begin(),
                    crcvec.end(),
                    crcvec.begin(), []( uint32_t w ){
      return (( w << 24 ) & 0xFF000000 ) //
             | (( w << 8 ) & 0x00FF0000 ) //
             | (( w >> 8 ) & 0x0000FF00 ) //
             | (( w >> 24 ) & 0x000000FF );
    } );
    const auto bytes = reinterpret_cast<const unsigned char*>( crcvec.data() );
    const auto crc32 = boost::crc<32, 0x4c11db7, 0x0, 0x0, false, false>( bytes,
                                                                          39
                                                                          * 4 );

    // Calculating the corruption code
    uint32_t corrupt = !(( head == 0x5 ) && ( tail == 0x5 ));
    corrupt += ( crc32 != data[39] ) * 2;
    corrupt += (( data[0] >> 2 ) & 0b11100 );

    return corrupt;
  }


  inline static uint8_t
  get_channel( const uint32_t idx )
  {
    if( idx <= 18 ){return idx-1;}
    if( idx > 19 ){ return idx-2;}
    return 36;// calibration channel
  }


  inline static uint8_t
  get_totflag( const uint32_t word, const uint32_t channel )
  {
    return word >> 30;
  }


  inline static uint16_t
  get_adcm( const uint32_t word, const uint32_t channel )
  {
    if( channel != 36 ){
      return ( word >> 20 ) & 0x3ff;
    } else {
      return -1;
    }
  }


  inline static uint16_t
  get_adc( const uint32_t word, const uint32_t channel )
  {
    if( channel == 36 ){
      return ( word >> 20 ) & 0x3ff;
    } else if( get_totflag( word, channel ) == 0 || //
               get_totflag( word, channel ) == 1 ){
      return ( word >> 10 ) & 0x3ff;
    } else {
      return -1;
    }
  }


  inline static uint16_t
  get_tot( const uint32_t word, const uint32_t channel )
  {
    uint16_t tot = -1;
    if( channel == 36 ){
      tot = ( word >> 10 ) & 0x3ff;
    } else if( get_totflag( word, channel ) == 2 || //
               get_totflag( word, channel ) == 3 ){
      tot = ( word >> 10 ) & 0x3ff;
    }
    if( ( tot >> 0x9 ) == 1 ){
      tot = ( tot & 0x1ff ) << 0x3;
    }
    return tot;
  }


  inline static uint16_t
  get_toa( const uint32_t word, const uint32_t channel )
  {
    return word  & 0x3ff;
  }


  inline static uint8_t
  get_validtp( const uint32_t tp )
  {
    const auto head = tp >> 28;

    if( head == 0xA || head == 0x9 ){
      return 1;
    } else {
      return 0;
    }
  }


  inline static uint8_t
  get_trigger_rawsum( const uint32_t tp, const uint8_t idx )
  {
    return ( tp >> ( 7 * ( 3-idx ))) & 0x7f;
  }


  inline static uint32_t
  decode_tc_val( const uint32_t value )
  {
    static uint32_t selTC9 = 0;
    int             mant   = value & 0x7;
    int             pos    = ( value >> 3 ) & 0xf;

    if( pos == 0 ){
      return mant << ( 1+selTC9 * 2 );
    } else {
      pos += 2;

      int decompsum = 1 << pos;
      decompsum |= mant << ( pos-3 );
      return decompsum << ( 1+selTC9 * 2 );
    }
  }


  void
  extend( const HGCROCv2RawData& rocdata )
  {
    // Checking data size is corrected first befor processing anything.
    this->nhalves   = this->get_nhalves( rocdata );
    this->nlinks    = this->get_nlinks( rocdata );
    this->nchannels = this->get_nchannels( rocdata );

    // Getting the per-data events
    this->_event.push_back( rocdata.event());
    this->_chip.push_back( rocdata.chip());
    this->_trigtime.push_back( get_trigger_offset( rocdata ));
    this->_trigwidth.push_back( get_trigwidth( rocdata ));

    std::vector<uint32_t> data( HGCROC_DATA_BUF_SIZE );

    // Looping over the halves
    for( uint8_t half = 0 ; half < this->nhalves; ++half ){
      std::copy(
        rocdata.data().begin()+HGCROC_DATA_BUF_SIZE * ( half+0 ),
        rocdata.data().begin()+HGCROC_DATA_BUF_SIZE * ( half+1 ),
        data.begin());

      this->_bxcounter.push_back( get_bxcounter( data[0] ));
      this->_eventcounter.push_back( get_eventcounter( data[0] ));
      this->_orbitcounter.push_back( get_orbitcounter( data[0] ));
      this->_corruption.push_back( get_corruption( data ));

      // Filling in Common mode channel information
      {
        this->_half.push_back( half );
        this->_channel.push_back( 37 );
        this->_adc.push_back( ( data[1] >> 10 ) & 0x3ff );
        this->_tot.push_back( 0 );
        this->_toa.push_back( 0 );
        this->_totflag.push_back( 0 );
        this->_adcm.push_back( 0 );

        this->_half.push_back( half );
        this->_channel.push_back( 38 );
        this->_adc.push_back( data[1] & 0x3ff );
        this->_tot.push_back( 0 );
        this->_toa.push_back( 0 );
        this->_totflag.push_back( 0 );
        this->_adcm.push_back( 0 );
      }

      for( unsigned int ichan = 1; ichan < N_READOUT_CHANNELS; ++ichan ){
        const uint32_t dataword = data[ichan+1];
        const int32_t  channel  = get_channel( dataword );
        this->_half.push_back( half );
        this->_channel.push_back( get_channel( ichan ));
        this->_totflag.push_back( get_totflag( dataword, channel ));
        this->_adcm.push_back( get_adcm( dataword, channel ));
        this->_tot.push_back( get_tot( dataword, channel ));
        this->_adc.push_back( get_adc( dataword, channel ));
        this->_toa.push_back( get_toa( dataword, channel ));
      }
    }

    // trigger info
    const int ntrigcellperlink = 4;

    for( int trig_link = 0; trig_link < this->nlinks; trig_link++ ){
      uint32_t tp = rocdata.trigger( trig_link );
      for( int i = 0; i < ntrigcellperlink; i++ ){
        this->_validtp.push_back( get_validtp( tp ));
        this->_channelsumid.push_back( i+( ntrigcellperlink * trig_link ));
        const uint32_t rawsum = get_trigger_rawsum( tp, i );
        this->_rawsum.push_back( rawsum );
        this->_decompresssum.push_back( decode_tc_val( rawsum ));
      }
    }
  }


  template<typename vartype>
  static pybind11::array_t<vartype>
  vector_to_array( const std::vector<vartype>& array ) // Simple
  {
    return pybind11::array_t<vartype>( array.size(), array.data() );
  }
};


PYBIND11_MODULE( _rocv2, m )
{
  namespace py =  pybind11;
  pybind11::class_<rocv2>( m, "rocv2" )

  // Only exposing the by filename string constructor
  .def( py::init<const std::string&>())

  // Per instance channel
  .def( "event", &rocv2::event )
  .def( "chip", &rocv2::chip )
  .def( "trigtime", &rocv2::trigtime )
  .def( "trigwidth", &rocv2::trigwidth )

  // Per half information
  .def_readonly( "nhalves", &rocv2::nhalves )
  .def( "corruption", &rocv2::corruption )
  .def( "bxcounter", &rocv2::bxcounter )
  .def( "eventcounter", &rocv2::eventcounter )
  .def( "orbitcounter", &rocv2::orbitcounter )

  // Per channel information
  .def_readonly( "nchannels", &rocv2::nchannels )
  .def( "half", &rocv2::half )
  .def( "channel", &rocv2::channel )
  .def( "adc", &rocv2::adc )
  .def( "adcm", &rocv2::adcm )
  .def( "toa", &rocv2::toa )
  .def( "tot", &rocv2::tot )
  .def( "totflag", &rocv2::totflag )

  // Per trigger link informato
  .def_readonly( "nlinks", &rocv2::nlinks )
  .def( "validtp", &rocv2::validtp )
  .def( "channelsumid", &rocv2::channelsumid )
  .def( "rawsum", &rocv2::rawsum )
  .def( "decompresssum", &rocv2::decompresssum )
  ;
}
