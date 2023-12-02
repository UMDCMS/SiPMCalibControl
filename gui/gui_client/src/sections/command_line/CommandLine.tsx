import React from 'react';
import { useForm, SubmitHandler } from 'react-hook-form';
import { useGlobalContext } from '../../contexts/GlobalContext';

import styles from './styles/CommandLine.module.css';

type Props = {};

interface FormValues {
  command: string;
}

const CommandLine = (props: Props) => {
  const { socketInstance } = useGlobalContext();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>();

  const onSubmit: SubmitHandler<FormValues> = (data, event) => {
    if (event) {
      if ((event.nativeEvent as any).submitter?.id === 'sendCommand') {
        console.log('commandSend Clicked');
        if (socketInstance) {
          socketInstance.emit('run-single-cmd', data.command);
        } else {
        }
      } else if ((event.nativeEvent as any).submitter?.id === 'lock') {
        // Code to handle the second submit button's action
        console.log('Submit Button 2 Clicked');
      }
    }
  };

  return (
    <div className={styles.formContainer}>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className={styles.commandInputContainer}>
          {errors.command && (
            <div className={styles.errorMsg}>This field is required (max length: 300).</div>
          )}
          <label htmlFor='command'>Command:</label>
          <button type='submit' id='lock'>
            Lock
          </button>
          <input
            type='text'
            placeholder='command'
            className={styles.commandInput}
            {...register('command', { required: true, maxLength: 300 })}
          />

          <button type='submit' id='sendCommand'>
            Execute
          </button>
        </div>
      </form>
    </div>
  );
};

export default CommandLine;
