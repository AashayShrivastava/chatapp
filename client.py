import socket
import threading

HOST = "127.0.0.1"
PORT = 1234

def listen_for_message_from_server(client):
    while True:
        try:
            message = client.recv(2048).decode("utf-8")
            if message:
                print(message)  # Display message as it is received from the server
            else:
                print("Empty message received from server.")
        except:
            print("Error receiving message from server. Connection closed.")
            client.close()
            break

def send_message_to_server(client):
    while True:
        message = input("Message (use '@username' to send direct message or type 'logout' to exit): ")
        if message:
            try:
                client.sendall(message.encode("utf-8"))
                if message.lower() == 'logout':
                    print("You have logged out.")
                    client.close()
                    break
            except:
                print("Error sending message to server. Connection closed.")
                client.close()
                break

def authenticate(client):
    while True:
        try:
            # Receive prompt from server (login or signup)
            server_message = client.recv(1024).decode("utf-8")
            print(server_message)
            
            # User responds with 'login' or 'signup'
            response = input("> ").strip().lower()
            client.sendall(response.encode("utf-8"))

            # Handle login or signup accordingly
            if response == 'login':
                username = input("Enter your username: ")
                password = input("Enter your password: ")

                client.sendall(username.encode("utf-8"))
                client.sendall(password.encode("utf-8"))

            elif response == 'signup':
                username = input("Choose a username: ")
                password = input("Choose a password: ")

                client.sendall(username.encode("utf-8"))
                client.sendall(password.encode("utf-8"))
            
            # Receive server's authentication result
            auth_result = client.recv(1024).decode("utf-8")
            print(auth_result)

            # If login/signup is successful, break the loop and start chatting
            if "successful" in auth_result.lower():
                break
        except:
            print("Error during authentication.")
            client.close()
            return False
    return True

def communicate_to_server(client):
    # Perform login or signup
    if authenticate(client):
        print("Authentication successful! You can now start sending messages.")

        # Start a thread to listen for messages from the server
        threading.Thread(target=listen_for_message_from_server, args=(client,)).start()

        # Send messages to the server
        send_message_to_server(client)
    else:
        print("Authentication failed. Exiting...")
        client.close()

def main():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((HOST, PORT))
        print(f"Connected to server at {HOST}:{PORT}")
    except:
        print("Connection unsuccessful.")
        return
    
    communicate_to_server(client)

if __name__ == "__main__":
    main()


