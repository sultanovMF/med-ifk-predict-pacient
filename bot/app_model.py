from pymongo import MongoClient


class AppModel:
    def __init__(self, db_name):
        self.__client = MongoClient("localhost", 27017)
        self.__db = self.__client[db_name]
        self.__patient_forms = self.__db["med-patient"]

    def add_to_db(self, form):
        self.__patient_forms.insert_one(form)

    def get_patient(self, name):
        criteria = {
            'name': name,
        }

        best_match = self.__patient_forms.find_one(criteria)

        return best_match

    def notify_doctor(self):
        pass
