# RentDuoer Discord Bot

## Description
The **RentDuoer Discord Bot** is a custom-built Discord bot designed to facilitate the hiring of gaming partners, inspired by platforms like PlayerDuo. Built with Python, the bot allows users to register as players, book gaming sessions, and manage rentals seamlessly within a Discord server. It features a user-friendly interface with slash commands (`/hi`), modals for booking and registration, and automated rental tracking using MongoDB for data storage. Deployed on Render.com with GitHub integration, the bot remains active using cron-job.org, ensuring 24/7 availability for users.

## Features
- **Registration**: Players can register with details like name, birthday, city, price per hour, social links, talents, and games they play.
- **Booking System**: Users can book a player for a specified duration and time, with automated acceptance/decline options.
- **Rental Management**: Tracks rental status (Pending, Accepted, Declined, Completed, Ended Early) with start/end times and pricing.
- **Interactive UI**: Uses nextcord buttons and modals for a smooth user experience.
- **Real-Time Updates**: Displays a digital clock for active rentals with an "End Early" option.

## Technologies Used
- **Programming Language**: Python 3.12.4
- **Framework/Library**: nextcord (Discord API), Flask (keep-alive server)
- **Database**: MongoDB (with pymongo 4.8.0)
- **Dependencies**: python-dotenv 1.0.1
- **Deployment**: Render.com, GitHub
- **Keep-Alive**: cron-job.org

## Installation

### Prerequisites
- Python 3.12.4
- Git
- MongoDB Atlas account (for database)
- Render.com account (for deployment)
- cron-job.org account (for keep-alive)

### Setup
1. **Clone the Repository**
git clone https://github.com/your-username/RentDuoer.git
cd RentDuoer
2. **Install Dependencies**
Create a virtual environment and install required packages:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
3. **Configure Environment Variables**
Create a `.env` file in the project root and add:
TOKEN=your_discord_bot_token
mongoURI=your_mongodb_atlas_connection_string
4. **Run Locally**
python RentDuoer.py


## Deployment

### On Render.com
1. Push your code to a GitHub repository.
2. Create a new Web Service on Render.com.
3. Connect your GitHub repository.
4. Set environment variables (`TOKEN`, `mongoURI`) in Render's dashboard.
5. Add the `Procfile` with `worker: python RentDuoer.py`.
6. Deploy the service.

### Keep-Alive with cron-job.org
1. Set up a cron job on cron-job.org to ping your Render app's URL (e.g., `https://your-app-name.onrender.com`) every 5 minutes.
2. Ensure the Flask app (`/`) is active to respond to pings.

## Usage

### Commands
- `/hi`: Displays options to book a player, register as a player, or submit a request (for users with "Customer" role).

### Registration
- Use the "Register" button to input details (name, birthday, city, show cam preference, price, social link, talents, games).
- Data is stored in the MongoDB `Players` collection.

### Booking
- Use the "Booking" button to enter boss username, player name, rent hours, and time.
- A request is sent to the player for acceptance/decline via the `AcceptDeclineView`.

### Rental Tracking
- Accepted bookings start a digital clock showing remaining time.
- Players can end rentals early using the "End Early" button.
- Status updates are logged in the `Rentals` collection.

## Database Schema
- **Players**: Stores player details (PlayerID, PlayerName, Birthday, City, ShowCam, PricePerHour, SocialLink, Talent, Games).
- **Rentals**: Tracks rental data (RentalID, PlayerID, DuoerID, RequestedStartTime, Duration, TotalPrice, Status, etc.).

## Contributing
Feel free to fork this repository, submit issues, or create pull requests. Contributions to improve features or fix bugs are welcome!

## Contact
For questions or support, reach out to tamnhint0905@gmail.com or connect via GitHub.