import os
from flask import request
import requests

from SLL import AppLogger, Logmessage, LogType


def catalog_headers():
    """x-api-key for the Catalog service, from INTERNAL_API_KEY.

    The Catalog requires a key on /restapi and /graphql; the API refuses to
    start without one (see startup_checks), so the empty case only happens
    under the development opt-out.
    """
    key = os.getenv("INTERNAL_API_KEY")
    return {"x-api-key": key} if key else {}


class RestApiRequestMethods:

    @staticmethod
    def get_request_with_params(url, params):
        """
        Faz uma requisição GET com parâmetros para a API externa
        """
        response = requests.get(url, params=params, headers=catalog_headers())
        if response.status_code != 200:
            raise Exception(f"Erro ao fazer requisição para {url}: {response.status_code}")
        return response

    @staticmethod
    def get_request_simple(url):
        response = requests.get(url, headers=catalog_headers())
        if response.status_code != 200:
            raise Exception("Erro ao buscar dados do shared-resources")
        return response
    
    
    @staticmethod
    def get_request_page(url, page_number, page_size):
        response = requests.get(url, params={"page": page_number, "page_size": page_size}, headers=catalog_headers())
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

        name = request.args.get('name')
        if name:
            query = f"""
            query{{
                disciplines(search: "{name}")  {{
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

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query}, headers=catalog_headers())
        data = response.json()
        disciplines = data.get("disciplines", [])
        return disciplines

    @staticmethod
    def get_all_periods_request():

        query = """query{
                    periods {
                        name
                    }
                    }"""

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query}, headers=catalog_headers())
        data = response.json()
        periods = data.get("periods", [])
        return periods

    @staticmethod
    def get_teachers_request():
        name = request.args.get('name')
        if name:
            query = f"""query{{
                                teachers(search: "{name}") {{
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


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query}, headers=catalog_headers())
        data = response.json()
        teachers = data.get("teachers", [])
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

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query}, headers=catalog_headers())
        data = response.json()
        rooms = data.get("rooms", [])
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

        response = requests.post(f"{os.getenv('URL_graph')}", json = {"query":query}, headers=catalog_headers())
        data = response.json()
        campus = data.get("campus",[])
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

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query}, headers=catalog_headers())
        data = response.json()
        types = data.get("types", [])
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

        search = request.args.get('search')

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


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query}, headers=catalog_headers())
        data = response.json()
        types = data.get("types", [])
        return types

    @staticmethod
    def get_specific_room():

        name = request.args.get('name')

        query = f"""
        query{{
            rooms(search: "{name}")
                {{
                    id
                    name
                    campus {{            
                        name
                        }}         
                }}
            }}
        """


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query}, headers=catalog_headers())
        data = response.json()
        room = data.get("rooms", [])
        return room

    @staticmethod
    def get_course_by_id(graduationId: str)-> list:
        if graduationId:
            query = f"""
            query{{
                courses(courseId: {graduationId})
                    {{
                        id
                        coordinator
                        name     
                    }}
                }}
            """
        else:
            AppLogger.log(
                Logmessage.ID_NOT_INFORMED,
                LogType.ERROR,
                collection="courses",
                id=graduationId,
            )
            raise Exception("ID de curso não informado ou nulo!")


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query}, headers=catalog_headers())
        data = response.json()
        course = data.get("courses", [])
        return course

    @staticmethod
    def get_teachers_by_id(teacherId: str)-> list:
        if teacherId:
            query = f"""
            query{{
                teachers(teacherId: "{teacherId}")
                    {{
                        id
                        email
                        name     
                    }}
                }}
            """
        else:
            AppLogger.log(
                Logmessage.ID_NOT_INFORMED,
                LogType.ERROR,
                collection="teachers",
                id=teacherId,
            )
            raise Exception("ID de professor não informado ou nulo!")


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query}, headers=catalog_headers())
        data = response.json()
        teachers = data.get("teachers", [])
        return teachers