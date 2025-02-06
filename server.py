import socket
import threading
import mysql.connector
from mysql.connector import Error

HOST = "127.0.0.1"
PORT = 1234
SERVER_LIMIT = 5
active_clients = []
lock = threading.Lock()  # To ensure thread safety when accessing the active_clients list

# Database connection details
DB_HOST = "localhost"
DB_USER = "root"  # Replace with your MySQL username
DB_PASSWORD = "cha@#nd321"  # Replace with your MySQL password
DB_NAME = "chatapp"


# Connect to MySQL Database
def connect_to_db():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


# Add a new user to the database
def add_user_to_db(username, password):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            connection.commit()
            return True
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return False
        finally:
            cursor.close()
            connection.close()


# Check if a username and password match (login)
def validate_user(username, password):
    connection = connect_to_db()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
            user = cursor.fetchone()
            return user is not None
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return False
        finally:
            cursor.close()
            connection.close()


# Function to handle login/signup logic
def authenticate_client(client):
    while True:
        client.sendall("Welcome! Type 'login' to log in or 'signup' to create a new account: ".encode())
        choice = client.recv(1024).decode("utf-8").strip().lower()

        if choice == "login":
            client.sendall("Enter your username: ".encode())
            username = client.recv(1024).decode("utf-8").strip()

            client.sendall("Enter your password: ".encode())
            password = client.recv(1024).decode("utf-8").strip()

            if validate_user(username, password):
                client.sendall(f"Login successful! Welcome back, {username}!\n".encode())
                return username
            else:
                client.sendall("Invalid username or password. Try again.\n".encode())

        elif choice == "signup":
            client.sendall("Choose a username: ".encode())
            username = client.recv(1024).decode("utf-8").strip()

            client.sendall("Choose a password: ".encode())
            password = client.recv(1024).decode("utf-8").strip()

            if add_user_to_db(username, password):
                client.sendall(f"Account created successfully! Welcome, {username}!\n".encode())
                return username
            else:
                client.sendall("Username already exists or an error occurred. Try again.\n".encode())

        else:
            client.sendall("Invalid choice. Please type 'login' or 'signup'.\n".encode())

def send_message_to_specific_client(recipient_username, message, sender_username=None):
    for user in active_clients:
        if user[0] == recipient_username:
            print(user[0])
            final_message = f"Direct from {sender_username}: {message}"
            send_message_to_client(user[1], final_message)
            return
    else:
        connection = connect_to_db()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT * FROM users WHERE username = %s", (recipient_username,))
                user = cursor.fetchone()
                if user:
                    connection = connect_to_db()
                    if connection:
                        
                        cursor = connection.cursor()
                        cursor.execute("INSERT INTO pending_message (username, password) VALUES (%s, %s)", (recipient_username, message))
                        connection.commit()
                        return True

            except mysql.connector.Error as err:
                print(f"Error: {err}")
                return False
            finally:
                cursor.close()
                connection.close()

    print(f"User {recipient_username} not found.")
def listen_for_message(client, username):
    while True:
        try:
            message = client.recv(2048).decode("utf-8")
            if message:
                if message.lower() == "logout":  # User sends a logout command
                    print(f"{username} has logged out")
                    remove_client(client)
                    send_message_to_all(f"{username} has left the chat.")  # Notify others
                    break
                elif message.startswith('@creategroup'):
                    lst = message.split(",")
                    groupname = lst[1].strip()
                    members = lst[2:]  # Get the members after group name
                    
                    connection = connect_to_db()
                    if connection:
                        try:
                            cursor = connection.cursor()
                            for member in members:
                                member = member.strip()
                                cursor.execute("INSERT INTO `group` (groupname, username) VALUES (%s, %s)", (groupname, member))
                            connection.commit()
                            client.sendall(f"Group {groupname} created successfully!\n".encode())
                        except mysql.connector.Error as err:
                            print(f"Error creating group: {err}")
                        finally:
                            cursor.close()
                            connection.close()
                elif message.startswith('@group'):
                    groupname = message.split()[0][1:]  # Extract the group name from the message
                    direct_message = ' '.join(message.split()[1:])  # Extract the message to be sent
                    connection = connect_to_db()
                    if connection:
                        try:
                            cursor = connection.cursor()
                            cursor.execute("SELECT * FROM `group` WHERE groupname = %s", (groupname,))
                            groupusers = cursor.fetchall()  # Fetch all users in the group
                            if groupusers:
                                for groupuser in groupusers:
                                    recipient_username = groupuser[2]  # Assuming the username is in the second column (index 2)
                                    print(f"Sending message to {recipient_username}")
                                    
                                    send_message_to_specific_client(recipient_username, direct_message, username)
                            else:
                                client.sendall(f"No users found in the group {groupname}.\n".encode())

                        except mysql.connector.Error as err:
                            print(f"Error fetching group members: {err}")
                            client.sendall(f"An error occurred while sending the message to the group.\n".encode())
                        finally:
                            cursor.close()
                            connection.close()

                    
                
                elif message.startswith('@'):
                    # Direct message format: @username message
                    recipient_username = message.split()[0][1:]
                    direct_message = ' '.join(message.split()[1:])
                    send_message_to_specific_client(recipient_username, direct_message, username)
                
                    
                else:
                    # Broadcast the message to all clients
                    final_message = f"{username} - {message}"
                    send_message_to_all(final_message)
            else:
                raise ConnectionResetError
        except:
            print(f"{username} has disconnected unexpectedly")
            remove_client(client)
            send_message_to_all(f"{username} has left the chat.")  # Notify others
            break





def send_message_to_client(client, final_message):
    try:
        print(client)
        client.sendall(final_message.encode())
    except:
        print("Error sending message to client")
        client.close()


def send_message_to_all(final_message):
    for user in active_clients:
        send_message_to_client(user[1], final_message)


def remove_client(client):
    with lock:
        for user in active_clients:
            if user[1] == client:
                active_clients.remove(user)
                break
    client.close()


def client_handler(client):
    username = authenticate_client(client)
    with lock:
        active_clients.append((username, client))
        connection = connect_to_db()
        if connection:
            
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM pending_message WHERE username = %s", (username,))
            user = cursor.fetchall()
            if user:
                for meaasages in user:
                    print(meaasages)
                    send_message_to_specific_client(meaasages[1],meaasages[2])
                
    print(f"{username} has connected")
    threading.Thread(target=listen_for_message, args=(client, username,)).start()


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.bind((HOST, PORT))
        print(f"Successfully bound to {HOST}:{PORT}")
    except socket.error as e:
        print(f"Unable to bind to {HOST}:{PORT} - {e}")
        return

    server.listen(SERVER_LIMIT)
    print("Server is listening...")

    while True:
        client, address = server.accept()
        print(f"Connection established with {address}")
        threading.Thread(target=client_handler, args=(client,)).start()


if __name__ == "__main__":
    main()
