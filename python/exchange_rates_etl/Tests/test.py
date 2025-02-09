import unittest
import requests
import json
import pandas as pd
from sqlalchemy import create_engine
import requests_mock # A python library for mocking REST APIs


class Test_case(unittest.TestCase):

    # Test GET request , Response to Dataframe
    def test_get_request(self):

        with open('sample_response.json', 'r') as sample_data:
            mock_response = sample_data.read()

        with requests_mock.Mocker() as mock:
            mock.register_uri('GET', 'http://api.exchangeratesapi.io/v1/latest?access_key=6e45c8ce217f5beca6893ac6968c5c2f',
                              text=mock_response)

            response = requests.get('http://api.exchangeratesapi.io/v1/latest?access_key=6e45c8ce217f5beca6893ac6968c5c2f').text
            # print(response)
            j = json.loads(response)
            df = pd.DataFrame.from_dict(j)
            self.assertFalse(df.empty)
            self.assertTrue(df.any)
            self.assertNotEqual(j, df.any)

    def test_Sqlite_db(self):
        engine = create_engine('sqlite://', echo=False)
        with open('sample_response.json', 'r') as sample_data:
            response = sample_data.read()
        raw_data = json.loads(response)
        # Serializing json
        data_dict = raw_data['rates']
        data_items = data_dict.items()
        data_list = list(data_items)
        df = pd.DataFrame(data_list, columns=['currency', 'rate'])
        df["date"] = raw_data["date"]
        df.to_sql('exhange_rates', con=engine, if_exists='replace')
        result1 = engine.execute("SELECT currency FROM exhange_rates WHERE currency = 'EUR' ").fetchall()
        result2 = engine.execute("SELECT currency FROM exhange_rates WHERE currency = 'GBP' ").fetchall()
        self.assertEqual('EUR', result1[0][0])
        self.assertEqual('GBP', result2[0][0])


if __name__ == '__main__':
    unittest.main()
