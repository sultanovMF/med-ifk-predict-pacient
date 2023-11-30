from bot.app_controller import AppController
from bot.app_model import AppModel

if __name__ == "__main__":
    token = "6541646393:AAEChO-gVmn2cBd9BAUpCAq_AKOT7ve-jsM"
    app_controller = AppController(token, AppModel("med"))

    app_controller.run()
