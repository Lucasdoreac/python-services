import os

import requests

class GetRequestMethods:
    
    @staticmethod
    def get_request_simple(url):
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception("Erro ao buscar dados do shared-resources")
        return response
    
    
    @staticmethod
    def get_request_page(url, page_number, page_size):
        response = requests.get(url, params={"page": page_number, "page_size": page_size})
        if response.status_code != 200:
            raise Exception("Erro ao buscar dados do shared-resources")
        return response


    @staticmethod
    def generate_url(endpoint):
        if os.getenv('URL_restapi') is not None:
            url = f"{os.getenv('URL_restapi')}/{endpoint}"
        else:
            raise Exception("Variavel de ambiente não existe ou não esta sendo acessada!")
        return url

