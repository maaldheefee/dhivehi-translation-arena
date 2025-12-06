#!/usr/bin/env python3
import subprocess
import sys
import os

def run_command(command):
    """Runs a shell command."""
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    while True:
        clear_screen()
        print("=== Dhivehi Translation Arena - User Manager ===")
        print("1. List Users")
        print("2. Add User")
        print("3. Remove User")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            print("\n--- User List ---")
            run_command("uv run --python 3.13 flask list-users")
            input("\nPress Enter to continue...")
            
        elif choice == '2':
            print("\n--- Add User ---")
            username = input("Enter username: ").strip()
            if not username:
                print("Username cannot be empty.")
                input("\nPress Enter to continue...")
                continue
                
            password = input("Enter password: ").strip()
            if not password:
                print("Password cannot be empty.")
                input("\nPress Enter to continue...")
                continue
            
            is_admin = input("Is admin? (y/n): ").lower().strip() == 'y'
            
            cmd = f"uv run --python 3.13 flask add-user {username} {password}"
            if is_admin:
                cmd += " --admin"
            
            run_command(cmd)
            input("\nPress Enter to continue...")
            
        elif choice == '3':
            print("\n--- Remove User ---")
            username = input("Enter username to remove: ").strip()
            
            if not username:
                 print("Username cannot be empty.")
                 input("\nPress Enter to continue...")
                 continue
                 
            confirm = input(f"Are you sure you want to remove user '{username}'? (y/n): ").lower().strip()
            if confirm == 'y':
                run_command(f"uv run --python 3.13 flask remove-user {username}")
            else:
                print("Operation cancelled.")
            
            input("\nPress Enter to continue...")
            
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
