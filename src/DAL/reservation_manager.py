from .mongodb_factory import MongoDBConnectionFactory
from datetime import datetime
from bson import ObjectId


class ReservationManager:

    def __init__(self):
        self.db = MongoDBConnectionFactory.get_db()
        self.reservation_collection = self.db.reservations
        self.rooms_collection = self.db.rooms
        self.buildings_collection = self.db.buildings
        self.events_collection = self.db.events

    def insert_reservation(self, room_id, course_id, date, start_time, end_time):
        # Fetch room details
        room = self.rooms_collection.find_one({'_id': ObjectId(room_id)})
        if room:
            building_id = room.get('buildingId')
            building = self.buildings_collection.find_one({'_id': ObjectId(building_id)})
            if building:
                # Check room availability within building timings
                opening_time = datetime.strptime(building.get("openAt"), "%I:%M:%S %p").time()
                closing_time = datetime.strptime(building.get("closeAt"), "%I:%M:%S %p").time()
                reservation_start_time = datetime.combine(date, start_time)
                reservation_end_time = datetime.combine(date, end_time)

                # Ensure requested time is within the building operating hours
                if opening_time <= start_time <= closing_time and opening_time <= end_time <= closing_time:
                    # Check if there's an existing reservation that conflicts with the new one
                    conflict = self.reservation_collection.find_one({
                        "roomId": room_id,
                        "startAt": {"$lt": reservation_end_time},
                        "endAt": {"$gt": reservation_start_time}
                    })

                    if not conflict:
                        reservation = {
                            "roomId": room_id,
                            "courseId": course_id,
                            "startAt": reservation_start_time,
                            "endAt": reservation_end_time
                        }
                        self.reservation_collection.insert_one(reservation)
                        print("Reservation successfully created.")
                    else:
                        print("This time slot is already booked.")
                else:
                    print("The room is not available at this time.")
            else:
                print("Building not found.")
        else:
            print("Room not found.")

    def insert_event(self, name, organizer, eventTypeId, odsTypeId, subscriptionLink, description, graduationId,
                     targetPublic, resources, expectedSubscribers, roomType, entrepreneuralPath, extensionProject, studentsMonitors, eventLogo):

        event = {
            "name": name,
            "organizer": organizer,
            "eventTypeId": eventTypeId,
            "odsTypeId": odsTypeId,
            "subscriptionLink": subscriptionLink,
            "description": description,
            "graduationId": graduationId,
            "targetPublic": targetPublic,
            "resources": resources,
            "expectedSubscribers": expectedSubscribers,
            "roomType": roomType,
            "entrepreneuralPath": entrepreneuralPath,
            "extensionProject": extensionProject,
            "studentsMonitors": studentsMonitors,
            "eventLogo": eventLogo
        }

        self.events_collection.insert_one(event)
