from SocketManager import SocketManager
import appleBot

# CONFIG
IP = "127.0.0.1"
PORT = 3490


if __name__ == "__main__":

    # initialize connection and wait for it to establish
    sock_manager = SocketManager(IP, PORT)
    while not sock_manager.connected:
        pass

    # initialize bot object
    bot = appleBot.AppleBot(sock_manager)

    # loop until connection breaks
    while sock_manager.connected:
        bot.loop()