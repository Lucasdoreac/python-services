import os
from typing import Any, Dict
import requests
from flask import jsonify
from datetime import datetime, timedelta
from DAL import *
from DAL.collections_repositories import EventsRepository
from sr_requests_module.request_methods import RestApiRequestMethods


# Initialize repository instances
university_repository = UniversityRepository()
buildings_repository = BuildingsRepository()
rooms_repository = RoomsRepository()
types_repository = TypesRepository()
reservations_repository = ReservationsRepository()
events_repository = EventsRepository()


class FlowController:

    @staticmethod
    def find_all_events():
        return events_repository.find_all()

    @staticmethod
    def find_events_by_user_email(email):
        return events_repository.find_all({"organizer.email": email})

    @staticmethod
    def find_reservation_by_event_id(event_id):
        return reservations_repository.find_all({"eventId": event_id})

    @staticmethod
    def find_event_by_event_id(event_id: str):
        return events_repository.find_by_id(event_id)

    def find_type_by_collection(collection: str):
        type_data = types_repository.get_type_by_collection(collection)
        if type_data:
            return jsonify(type_data), 200
        else:
            return jsonify({'error': 'There is no such type'}), 404

    def register_reservation_from_json(data: Dict[str, Any]):
        """
        Processa os dados de reserva recebidos via JSON e insere a reserva no sistema.

        Converte a data de reserva (no formato ISO com 'Z') para um objeto datetime,
        define o início da reserva e calcula o fim (adicionando duas horas),
        e então delega a inserção ao ReservationManager.

        Args:
            data (Dict[str, Any]): Dados do JSON da requisição.

        Returns:
            Response: Objeto Flask Response com mensagem de sucesso e status HTTP 201,
                      ou mensagem de erro e o status HTTP correspondente.
        """
        try:
            event_id = data["eventId"]
            reservation_date_str = data["reservationDate"]
            room_id = data["roomId"]

            reservation_date = datetime.strptime(reservation_date_str, "%Y-%m-%dT%H:%M:%S.%fZ")

            reservation_start = reservation_date
            reservation_end = reservation_start + timedelta(hours=2)

            if FlowController.already_reservation(reservation_start,room_id):
                return jsonify({'error': 'Room already reserved for this time'}), 400

            reservation_system = ReservationManager()
            reservation_system.insert_reservation(
                room_id,
                event_id,
                reservation_start.date(),
                reservation_start.time(),
                reservation_end.time()
            )

            return jsonify({'success': "Reservation attempted"}), 201

        except KeyError as e:
            return jsonify({'error': f'Missing field: {str(e)}'}), 400
        except ValueError as e:
            return jsonify({'error': f'Invalid data format: {str(e)}'}), 400


    def filter_reservation_by_date(date: str):
        try:
            # Extracting date
            date_str = date

            # Converting date to datetime object
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')

            filter_by_date = reservations_repository.get_reservation_by_date(date_obj)

            return filter_by_date

        except KeyError as e:
            return jsonify({'error': f'Missing field: {str(e)}'}), 400
        except ValueError as e:
            return jsonify({'error': f'Invalid data format: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'error': f"An error ocucred: {str(e)}"}), 400


    def filter_available_rooms(self, date_str: str, time_str: str, page: int, page_size: int):
        """
            Recebe uma data e um horário e retorna uma lista de salas disponíveis,
            removendo da lista de todas as salas aquelas com reservas que abrangem o horário informado.
            Retorna os campos "id", "name" e "campus" de cada sala disponível.
        """
        # Obter os 'IDs' das salas indisponíveis para o horário informado
        reservation_system = ReservationManager()
        unavailable_room_ids = reservation_system.find_unavailable_room_ids_by_date(date_str, time_str)

        # Buscar todas as salas cadastradas no shared-resources, paginadas
        all_rooms, pagination_config = self.find_all_rooms(page, page_size)

        # Filtrar as salas disponíveis: remover as que estão na lista de indisponíveis
        available_rooms = [
            {
                "id": room.get("id"),
                "name": room.get("name"),
                "campus": room.get("campus")
            }
            for room in all_rooms
            if room.get("id") not in unavailable_room_ids
        ]

        return available_rooms, pagination_config

    def find_room_by_id(room_id: str):
        """
        Busca sala cadastrada no shared-resources pelo Id
        :param room_id:
        :return:
        """
        try:
            url = f"{os.getenv('URL_restapi')}/rooms?room_id={room_id}"
            response = requests.get(url)
            if response.status_code != 200:
                raise Exception("Erro ao buscar sala do shared-resources")
            return response.json()
        except Exception as e:
            return jsonify({'error': f"An error ocucred: {str(e)}"}), 400

    def find_all_rooms(self, page: int, page_size: int):
        """
            Busca todas as salas cadastradas no shared-resources, utilizando paginação.
        """
        url = RestApiRequestMethods.generate_url("/rooms")
        response = RestApiRequestMethods.get_request_page(url, page, page_size)
        #if response.status_code != 200:
       #     raise Exception("Erro ao buscar salas do shared-resources")

        rooms_json = response.json()
        # Se a resposta possuir paginação, os dados estarão no campo "data"
        all_rooms = rooms_json.get("data", rooms_json)
        pagination_config = rooms_json.get("pagination", {})
        return all_rooms, pagination_config

    def find_types_by_collection(collection: str):
        """
            Busca os tipos cadastrados no shared-resources com base na coleção.
            :param collection: Nome da coleção a ser buscada.
            :return: JSON com os dados dos tipos ou mensagem de erro.
            """
        try:
            url_base = os.getenv('URL_restapi')
            url = f"{url_base}/types/?collection_name={collection}"

            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            types = [types_item for item in data for types_item in item.get('types', [])]
            if types:
                return {'types': types}
            return jsonify({'error': "Type not found"}), 404
        except Exception as e:
            return jsonify({'error': f"An error ocucred: {str(e)}"}), 400


    def create_event(data: Dict[str, Any]):
        """
            Cria um evento a partir dos dados recebidos e insere-o no sistema.

            Esta função extrai as informações do organizador e demais atributos do evento,
            constrói o objeto de dados do evento e delega a inserção ao ReservationManager.

            Args:
                data (Dict[str, Any]): Dados do evento recebidos via JSON.

            Returns:
                Response: Objeto Flask Response contendo o ID do evento criado e o status HTTP 201,
                          ou uma mensagem de erro e o status HTTP correspondente.
        """
        try:
            # Monta o objeto de dados do evento usando função auxiliar
            event_data = FlowController.event_data_build(data)

            reservation_manager = ReservationManager()
            event_id = reservation_manager.insert_event(event_data)
            return jsonify({"eventId": event_id}), 201

        except KeyError as e:
            error_msg = f'Missing field: {str(e)}'
            return jsonify({'error': error_msg}), 400

        except Exception as e:
            return jsonify({'error': str(e)}), 500


    def update_event(event_id: str, data: Dict[str, Any]):
        """
            Atualiza um evento existente com base no ID e nos dados fornecidos.

            Essa função reconstrói o objeto de dados do evento, garantindo que os dados
            do organizador sejam mantidos em um único campo "organizer", evitando criar
            novos campos para as informações do organizador.

            Args:
                event_id (str): ID do evento a ser atualizado.
                data (Dict[str, Any]): Dados atualizados do evento recebidos via JSON.

            Returns:
                Response: Objeto Flask Response contendo o ID do evento atualizado e o status HTTP 200,
                          ou uma mensagem de erro e o status HTTP correspondente.
        """
        try:
            # Reconstrói os dados do evento para manter o formato consistente
            event_data = FlowController.event_data_build(data)

            reservation_manager = ReservationManager()
            updated_event_id = reservation_manager.update_event(event_id, event_data)
            return jsonify({"eventId": updated_event_id}), 200

        except KeyError as e:
            error_msg = f'Missing field: {str(e)}'
            return jsonify({'error': error_msg}), 400

        except Exception as e:
            return jsonify({'error': 'An error occurred while updating the event'}), 500


    def event_data_build(data: Dict[str, Any]):
        """
            Constrói o objeto de dados do evento com base nos dados recebidos.

            Essa função extrai informações essenciais, como dados do organizador, e monta
            um dicionário com o formato esperado para armazenamento, garantindo que os dados
            do organizador fiquem concentrados no campo "organizer".

            Args:
                data (Dict[str, Any]): Dados brutos do evento recebidos via JSON.

            Returns:
                dict: Dicionário contendo os dados formatados do evento.

            Raises:
                ValueError: Se o campo "userEmail" estiver ausente.
        """
        teacher_email = data.get("userEmail")
        if not teacher_email:
            raise ValueError("User email is required")
        teacher_phone = data.get("telefone", "")
        teacher_name = teacher_email.split("@")[0]
        organizer = {
            "name": teacher_name,
            "email": teacher_email,
            "phone": teacher_phone
        }
        return {
            "name": data.get("tituloEvento", ""),
            "organizer": organizer,
            "eventTypeId": data.get("classificacao", ""),
            "odsId": data.get("odsId", ""),
            "subscriptionLink": "",
            "description": data.get("descricaoEvento", ""),
            "graduationId": data.get("courseId", ""),
            "targetPublic": data.get("publicoAlvo", ""),
            "resources": data.get("recursosNecessarios", ""),
            "expectedSubscribers": data.get("numeroParticipantes", ""),
            "roomType": data.get("espacos", ""),
            "entrepreneuralPath": data.get("trilhaDesc", ""),
            "extensionProject": data.get("projetoDesc", ""),
            "studentsMonitors": data.get("alunosMonitores", ""),
            "eventLogo": "",
            "status": data.get("status", "requested"),
        }

    def already_reservation(start_at:datetime,room_id: str)-> bool:
        """
            Verifica se já existe uma reserva para a sala e horário informados.
            :param start_at: Horário de início da reserva.
            :param roomId: ID da sala a ser verificada.
            :return: True se já existe reserva, False caso contrário.
        """
        start_at_limit = start_at + timedelta(hours=2)
        query = {
            "startAt": {
                "$gte": start_at,
                "$lt": start_at_limit
            },
            "roomId": room_id
        }
        return reservations_repository.find_by_query(query) is not None


