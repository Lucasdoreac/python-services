import os
from flask import request
import requests
from pycparser.c_ast import Switch


class RestApiRequestMethods:
    
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

class GraphQlRequestMethods:

    @staticmethod
    def get_disciplines_request():

        search = request.headers.get('search')
        if search:
            query = f"""
            query{{
                disciplines(search: "{search}")  {{
                    name
                }}
            }}
            """
        else:
            query = """query{
                       disciplines {
                         name
                       }
                       }"""

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        disciplines = data.get("data", {}).get("disciplines", [])
        return disciplines

    @staticmethod
    def get_all_periods_request():

        query = """query{
                    periods {
                        name
                    }
                    }"""

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        periods = data.get("data", {}).get("periods", [])
        return periods

    @staticmethod
    def get_teachers_request():
        search = request.headers.get('search')
        if search:
            query = f"""query{{
                                teachers(search: "{search}") {{
                                    name
                                    id
                                }}
                                }}"""
        else:
            query = """query{
                        teachers {
                            name
                            id
                        }
                        }"""


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        teachers = data.get("data", {}).get("teachers", [])
        return teachers

    @staticmethod
    def get_all_rooms_request():
        query= """query{
                  rooms{
                    name
                     campus{
                      name
                      id
                    }
                  }
                }"""

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        rooms = data.get("data", {}).get("rooms", [])
        return rooms

    @staticmethod
    def get_all_campus_request():

        query = """
        query {
            campus {
                id
                name
            }
        }
        """

        response = requests.post(f"{os.getenv('URL_graph')}", json = {"query":query})
        data = response.json()
        campus = data.get("data",{}).get("campus",[])
        return campus

    @staticmethod
    def get_all_types_request():
        query = """query{
                      types{
                        collection
                        types {
                          id
                          name
                        }
                      }                    
                    }"""

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        types = data.get("data", {}).get("types", [])
        return types

    @staticmethod
    def get_all_request_by_collection(collectionName):
        match collectionName:
            case "periods":
                return GraphQlRequestMethods.get_all_periods_request()
            case "disciplines":
                return GraphQlRequestMethods.get_disciplines_request()
            case "teachers":
                return GraphQlRequestMethods.get_teachers_request()
            case "campus":
                return GraphQlRequestMethods.get_all_campus_request()
            case "rooms":
                return GraphQlRequestMethods.get_all_rooms_request()
            case "types":
                return GraphQlRequestMethods.get_all_types_request()
            case _:
                raise Exception("Erro: nome de coleção invalido ao utilizar a função get_all_request_by_collection!")

    @staticmethod
    def get_specific_type():

        search = request.headers.get('search')

        query = f"""
        query{{
            types(search: "{search}"){{
                collection
                    types{{
                        name
                        type
                        }}
                    }}
                }}
        """


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        types = data.get("data", {}).get("types", [])
        return types

    @staticmethod
    def get_specific_room():

        search = request.headers.get('search')

        query = f"""
        query{{
            rooms(search: "{search}")
                {{
                    id
                    name
                    campus {{            
                        name
                        }}         
                }}
            }}
        """


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        room = data.get("data", {}).get("rooms", [])
        return room










