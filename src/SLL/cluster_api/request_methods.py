import os
from flask import request
import requests

from SLL import AppLogger, Logmessage, LogType


class RestApiRequestMethods:

    @staticmethod
    def get_request_with_params(url, params):
        """
        Faz uma requisição GET com parâmetros para a API externa
        """
        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f"Erro ao fazer requisição para {url}: {response.status_code}")
        return response

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

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
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

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
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


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
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

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        rooms = data.get("rooms", [])
        return rooms

    @staticmethod
    def get_offers_by_weekday_request(weekday: int, year: int, semester: int):
        """
        Ofertas (aulas do semestre) com aula nesse dia da semana (ISO: 1 = segunda).
        Levanta exceção se o catálogo falhar: sem as ofertas não dá para
        afirmar que uma sala está livre.
        """
        query = f"""query{{
                    offers(searchWeekday: {int(weekday)}, searchYear: {int(year)}, searchSemester: {int(semester)}) {{
                        room {{ id }}
                        period {{ name }}
                    }}
                    }}"""

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        if response.status_code != 200 or "errors" in data:
            raise Exception(f"Erro ao buscar ofertas no shared-resources: {data.get('errors')}")
        return data.get("offers") or []

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

        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
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


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
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


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
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


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
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


        response = requests.post(f"{os.getenv('URL_graph')}", json={"query": query})
        data = response.json()
        teachers = data.get("teachers", [])
        return teachers