from pymongo import MongoClient


class AppModel:
    def __init__(self, db_name):
        self.__client = MongoClient("localhost", 27017)
        self.__db = self.__client[db_name]
        self.__patient_forms = self.__db["med-patient"]

    def add_to_db(self, user_form: {}):
        ...
        # patient_form = {
        #     "full_name": user_model.name,
        #     "alcoholic": user_model.alcoholic,
        #     "date": datetime.datetime.now(tz=datetime.timezone.utc),
        # }
        # self.__patient_forms.insert_one(patient_form)
