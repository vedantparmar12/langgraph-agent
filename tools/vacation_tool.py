from typing import Any, Dict, List, Type
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import requests

class VacationInput(BaseModel):
    location: str = Field(description="Country name to get information about (e.g., 'Germany', 'Japan', 'United States')")
    user_id: str = Field(default="default_user", description="User ID (defaults to 'default_user')")

class VacationTool(BaseTool):
    name: str = "vacation_finder"
    description: str = "Gets country information including currency, capital, and region using REST Countries API. Requires a country name."
    args_schema: Type[BaseModel] = VacationInput

    def fetch_country_data(self, country_name: str) -> Dict:
        api_url = f"https://restcountries.com/v3.1/name/{country_name}?fields=name,capital,currencies,region"
        response = requests.get(api_url)

        if response.status_code != 200:
            return {"error": f"Failed to get country info: {response.status_code}"}

        data = response.json()
        if not data or len(data) == 0:
            return {"error": f"No country found with name: {country_name}"}

        return data[0]

    def _run(self, **kwargs) -> str:
        location = kwargs.get('location')
        user_id = kwargs.get('user_id', 'default_user')

        if not location:
            return "Please provide a country name."

        country_data = self.fetch_country_data(location)

        if "error" in country_data:
            return f"Error fetching country information: {country_data['error']}"

        country_info = self.extract_country_details(country_data)
        return self.format_country_information(country_info, user_id)


    def extract_country_details(self, data: Dict) -> Dict:
        country_info = {
            'name': data.get('name', {}).get('common', 'Unknown'),
            'official_name': data.get('name', {}).get('official', 'Unknown'),
            'capital': ', '.join(data.get('capital', ['Unknown'])),
            'region': data.get('region', 'Unknown'),
            'currencies': self.format_currency_information(data.get('currencies', {}))
        }
        return country_info

    def format_currency_information(self, currencies_data: Dict) -> str:
        if not currencies_data:
            return 'Unknown'

        currency_list = []
        for code, details in currencies_data.items():
            name = details.get('name', code)
            symbol = details.get('symbol', '')
            if symbol:
                currency_list.append(f"{name} ({code}) - {symbol}")
            else:
                currency_list.append(f"{name} ({code})")

        return ', '.join(currency_list)

    def format_country_information(self, country_info: Dict, user_id: str) -> str:
        response = f"Country Information for {country_info['name']} (User: {user_id}):\n\n"
        response += f"Official Name: {country_info['official_name']}\n"
        response += f"Capital: {country_info['capital']}\n"
        response += f"Region: {country_info['region']}\n"
        response += f"Currency: {country_info['currencies']}\n"

        return response

    async def _arun(self, **kwargs) -> str:
        return self._run(**kwargs)