import React from 'react';
import { Formik, Form, Field, ErrorMessage } from 'formik';
import { useGlobalContext } from '../../contexts/GlobalContext';

import styles from './styles/CommandLine.module.scss';

type Props = {};

interface FormValues {
  command: string;
}

const CommandLine2 = (props: Props) => {
  const { socketInstance } = useGlobalContext();
  // const [command, setCommand] = useState<string>(''); // command to send to server

  const initialValues: FormValues = { command: '' };

  const validate = (values: FormValues) => {
    const errors: Partial<FormValues> = {};
    if (!values.command) {
      errors.command = 'Required';
    }
    return errors;
  };

  const onSubmit = (values: FormValues, { setSubmitting }: any) => {
    if (socketInstance) {
      socketInstance.emit('run-single-cmd', values.command);
    } else {
    }
    setSubmitting(false);
  };

  // const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
  //   setCommand(event.target.value);
  // };

  return (
    <div>
      <Formik initialValues={initialValues} validate={validate} onSubmit={onSubmit}>
        {({ isSubmitting }) => (
          <Form>
            <div>
              <label htmlFor='command'>Command:</label>
              <Field type='text' id='command' name='command' />
              <ErrorMessage name='command' component='div' />
            </div>
            <div>
              <button type='submit' disabled={isSubmitting}>
                Submit
              </button>
            </div>
          </Form>
        )}
      </Formik>
      {/* simple text input with label  and a submit button, all inline. */}

      {/* <label htmlFor='command-line'>Command Line</label>
      <input type='text' id='command-line' value={command} onChange={handleChange} />
      <button onSubmit={commandSend}>Submit</button> */}
    </div>
  );
};

export default CommandLine2;
