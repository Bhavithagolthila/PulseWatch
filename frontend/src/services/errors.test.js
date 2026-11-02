import {describe, it, expect} from 'vitest';
import {getErrorMessage} from './errors';

describe('getErrorMessage', () => {
  it('returns string details unchanged', () => {
    expect(getErrorMessage({response: {data: {detail: 'Monitor not found.'}}})).toBe('Monitor not found.');
  });

  it('flattens FastAPI validation arrays instead of returning objects', () => {
    const error = {response: {data: {detail: [{loc: ['body', 'name'], msg: 'Value error, Name is too short.'}]}}};
    expect(getErrorMessage(error)).toBe('Name is too short.');
  });

  it('explains network failures', () => {
    expect(getErrorMessage({message: 'Network Error'})).toMatch(/backend running/);
  });

  it('falls back to the supplied message', () => {
    expect(getErrorMessage({response: {data: {}}}, 'Could not save.')).toBe('Could not save.');
  });
});
