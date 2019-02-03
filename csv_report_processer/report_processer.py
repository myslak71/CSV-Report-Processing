import os

import pandas as pd
import pycountry

from csv_report_processer.config import LOGGER


class ReportProcesser(object):
    """

    """
    _columns = ('date', 'country_code', 'impressions', 'clicks')

    @classmethod
    def process_csv_report(cls, input_path, output_path, error_path=None):
        """
        Report processing function.

        For given .csv file creates output .csv file and optional error .csv file.
        In case of critical errors, sends error message to output and does not
        create .csv file.

        :param input_path: str
            Path to input .csv file
            Supported file encoding: UTF-8, UTF-16
        :param output_path: str
            Path to output .csv file
        :param error_path: str, default None
            Path to output error .csv file
            If specified, but no errors has occured, file is not created.
        """
        try:
            df = ReportProcesser._open_report(input_path, cls._columns)
        except UnicodeError:
            LOGGER.error('Invalid file encoding - supported encoding: UTF-8, UTF-16\nCould not process the file.')
        except FileNotFoundError:
            LOGGER.error(f'Input file {input_path} does not exist\nCould not process the file.')
        else:
            ReportProcesser._convert_data(df)

            df_valid = df[df['error'] != 1]
            df_error = df[df['error'] == 1]

            if df_error.empty or not error_path:
                df_valid = df_valid.groupby(['date', 'country_code'], as_index=False).agg(cls._aggregate_rows)
                pd.concat([df_valid, df_error]).to_csv(output_path, index=False, header=False,
                          columns=cls._columns, line_terminator='\n')
                word = 'out' if df_error.empty else ''
                LOGGER.info(f"File has been converted with{word} errors and saved at {output_path}")

            elif error_path:
                df_valid = df_valid.groupby(['date', 'country_code'], as_index=False).agg(cls._aggregate_rows)
                df_valid.to_csv(output_path, index=False, header=False,
                                columns=cls._columns, line_terminator='\n')
                df_error.to_csv(error_path, index=False, header=False,
                                columns=cls._columns, line_terminator='\n')
                LOGGER.info(f"File has been converted with errors and saved at {output_path}")
                LOGGER.info(f"Invalid data has been excluded from the result and saved at {error_path}")

    @staticmethod
    def _aggregate_rows(row):
        return row.astype(int).sum()

    @staticmethod
    def _open_report(input_path, columns):
        """
        Csv file opening function.
        Opens .csv report.
        Supported file encoding: UTF-8, UTF-16


        :param input_path: str
            Path to input .csv file
        :param columns:
        :return:
        """
        try:
            df = pd.read_csv(input_path, names=columns, index_col=False,
                             keep_default_na=False)
        except UnicodeDecodeError:
            df = pd.read_csv(input_path, names=columns, index_col=False,
                             keep_default_na=False, encoding='utf-16')
        return df



    @classmethod
    def _convert_data(cls, df):
        """

        :param df:
        :return:
        """
        df['country_code'] = df['country_code'].apply(cls._convert_state_to_country)

        df['error'] = 0

        for row in df.itertuples():
            try:
                df.at[row.Index, 'date'] = pd.to_datetime(row.date).strftime('%Y-%m-%d')
            except ValueError:
                LOGGER.error(f"Row {row.Index}: Following date could not be converted: {df.at[row.Index, 'date']}\n")
                df.at[row.Index, 'error'] = 1

            try:
                df.at[row.Index, 'clicks'] = float(str(row.clicks).rstrip('%')) / 100
                df.at[row.Index, 'clicks'] = round(df.at[row.Index, 'clicks'] * int(row.impressions))
            except Exception as e:
                if str(e).startswith('invalid literal for int() with base 10: '):
                    error_message = str(e).replace('invalid literal for int() with base 10: ',
                                                   f'Row {row.Index}: Following impression number '
                                                   f'could not be converted: ')
                else:
                    error_message = str(e).replace('could not convert string to float: ',
                                                   f'Row {row.Index}: Following CTR could not be converted: ')
                df.at[row.Index, 'error'] = 1
                LOGGER.error(error_message)

    @staticmethod
    def _convert_state_to_country(state_name):
        """

        :param state_name:
        :return:
        """
        try:
            state = pycountry.subdivisions.lookup(state_name)
            country = pycountry.countries.get(alpha_2=state.country_code)
            return country.alpha_3
        except LookupError:
            return 'XXX'


if __name__ == '__main__':
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ReportProcesser.process_csv_report(BASE_DIR + '/test.csv',
                                       BASE_DIR + '/output_test.csv',
                                       BASE_DIR + '/errors.csv')
