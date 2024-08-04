import nextcord
from nextcord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
from db_connection import get_database_connection, close_database_connection
from dotenv import load_dotenv
import os
import pymongo
from pymongo.errors import PyMongoError
from threading import Thread
from flask import Flask

load_dotenv()
TOKEN = os.getenv('TOKEN')
mongoURI = os.getenv('mongo_URI')

# Bot setup
intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

def setup_mongodb():
    db = get_database_connection()
    
    # Create collections if they don't exist
    if 'Players' not in db.list_collection_names():
        db.create_collection('Players')
    
    if 'Duoers' not in db.list_collection_names():
        db.create_collection('Duoers')
    
    if 'Rentals' not in db.list_collection_names():
        db.create_collection('Rentals')

    # Create indexes
    db.Players.create_index('PlayerID', unique=True)
    db.Duoers.create_index('DuoerID', unique=True)
    db.Rentals.create_index([('PlayerID', 1), ('DuoerID', 1), ('RequestedStartTime', 1)])

# Call this function when your bot starts
setup_mongodb()

# Slash command
@bot.slash_command(name="hi", description="Show booking and register options")
async def hi(interaction: nextcord.Interaction):
    try:
        await interaction.response.defer()
    except nextcord.errors.NotFound:
        # Interaction has already been responded to or timed out
        return

    try:
        view = MainView()
        await interaction.followup.send("Choose an option:", view=view)
    except nextcord.errors.HTTPException as e:
        print(f"Error sending followup: {e}")

# Main view with booking and register buttons
class MainView(nextcord.ui.View):
    def __init__(self):
        super().__init__()
    
    @nextcord.ui.button(label="Booking", style=nextcord.ButtonStyle.primary)
    async def booking_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(BookingModal())

    @nextcord.ui.button(label="Register", style=nextcord.ButtonStyle.secondary)
    async def register_button(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(RegisterModal())

# Booking modal
class BookingModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="Booking Information")
        self.player_username = nextcord.ui.TextInput(label="Player Identifier", placeholder="Enter @mention, username, or display name")
        self.duoer_name = nextcord.ui.TextInput(label="Duoer Name", placeholder="Enter duoer's name")
        self.rent_hours = nextcord.ui.TextInput(label="Rent Hours", placeholder="Enter number of hours")
        self.rent_time = nextcord.ui.TextInput(label="Rent Time", placeholder="Enter rent time (DD/MM/YYYY HH:MM)")
        
        self.add_item(self.player_username)
        self.add_item(self.duoer_name)
        self.add_item(self.rent_hours)
        self.add_item(self.rent_time)

    async def callback(self, interaction: nextcord.Interaction):
        try:
            await interaction.response.defer()
        except nextcord.errors.NotFound:
            print("Interaction has already been responded to or timed out")
            return

        try:
            db = get_database_connection()
        
            print(f"Debug: Searching for player: {self.player_username.value}")
            print(f"Debug: Guild members: {[member.name for member in interaction.guild.members]}")
            
            # Check if the input is a user mention
            if self.player_username.value.startswith('<@') and self.player_username.value.endswith('>'):
                player_id = self.player_username.value[2:-1]
                if player_id.startswith('!'):
                    player_id = player_id[1:]
                player = interaction.guild.get_member(int(player_id))
                print(f"Debug: Mention detected. Player ID: {player_id}, Player found: {player is not None}")
            else:
                # Try to find the player by username or display name
                player = None
                for member in interaction.guild.members:
                    if member.name.lower() == self.player_username.value.lower() or \
                       member.display_name.lower() == self.player_username.value.lower():
                        player = member
                        break
                print(f"Debug: Name search. Player found: {player is not None}")
            
            if player:
                player_id = str(player.id)
                print(f"Debug: Player found. ID: {player_id}")
            else:
                await interaction.followup.send("Player not found. Please check the username, display name, or use @mention and try again.")
                return

            db.Players.update_one(
                {'PlayerID': player_id},
                {'$set': {'PlayerName': self.player_username.value}},
                upsert=True
            )
            
            duoer = db.Duoers.find_one({'DuoerName': self.duoer_name.value})
        
            if duoer:
                duoer_id = duoer['DuoerID']
                price_per_hour = duoer['PricePerHour']
                requested_start_time = datetime.strptime(self.rent_time.value, "%d/%m/%Y %H:%M")
                rent_hours = float(self.rent_hours.value)
                total_price = int(rent_hours * price_per_hour)
            
                db.Rentals.insert_one({
                    'PlayerID': player_id,
                    'DuoerID': duoer_id,
                    'RequestedDuration': rent_hours,
                    'TotalPrice': total_price,
                    'RequestedStartTime': requested_start_time,
                    'Status': 'Pending'
                })
            
                view = AcceptDeclineView(player_id, duoer_id, rent_hours, requested_start_time)
                await interaction.channel.send(f"New booking request from <@{player_id}> for <@{duoer_id}>. Total price: {total_price // 1000}K VND. Requested start time: {requested_start_time}. Please accept or decline:", view=view)
            
                await interaction.followup.send("Booking request submitted. Waiting for duoer's confirmation.")
            else:
                await interaction.followup.send("Duoer not found. Please check the name and try again.")
    
        except PyMongoError as e:
            error_message = f"A database error occurred: {str(e)}"
            print(error_message)
            await interaction.followup.send(error_message)
        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            print(f"Debug: {error_message}")
            await interaction.followup.send(error_message)

# Register modal
class RegisterModal(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(title="Register as Duoer", timeout=5 * 60)
        
        self.personal_info = nextcord.ui.TextInput(
            label="Name, Birthday, City, Show Cam (yes/no)",
            placeholder="Format: Name, DD/MM/YYYY, City, yes/no",
            style=nextcord.TextInputStyle.paragraph
        )
        
        self.price = nextcord.ui.TextInput(
            label="Price per hour (in K VND)",
            style=nextcord.TextInputStyle.short
        )
        
        self.social_link = nextcord.ui.TextInput(
            label="Facebook/Instagram link",
            style=nextcord.TextInputStyle.short
        )
        
        self.talent = nextcord.ui.TextInput(
            label="Talents",
            style=nextcord.TextInputStyle.paragraph
        )
        
        self.games = nextcord.ui.TextInput(
            label="Games you can play",
            style=nextcord.TextInputStyle.paragraph
        )
        
        self.add_item(self.personal_info)
        self.add_item(self.price)
        self.add_item(self.social_link)
        self.add_item(self.talent)
        self.add_item(self.games)

    async def callback(self, interaction: nextcord.Interaction):
        try:
            personal_info_parts = self.personal_info.value.split(',')
            if len(personal_info_parts) != 4:
                raise ValueError("Personal info must contain 4 parts separated by commas")
        
            name = personal_info_parts[0].strip()
            birthday = personal_info_parts[1].strip()
            city = personal_info_parts[2].strip()
            show_cam = personal_info_parts[3].strip().lower()

            if show_cam not in ['yes', 'no']:
                raise ValueError("Show cam must be 'yes' or 'no'")

            # Validate birthday format
            try:
                datetime.strptime(birthday, "%d/%m/%Y")
            except ValueError:
                raise ValueError("Birthday must be in DD/MM/YYYY format")

            # Convert price to VND (removing 'K' and multiplying by 1000)
            price_in_vnd = int(float(self.price.value.replace('K', '')) * 1000)

            db = get_database_connection()
            db.Duoers.update_one(
                {'DuoerID': str(interaction.user.id)},
                {
                    '$set': {
                        'DuoerName': name,
                        'Birthday': birthday,
                        'City': city,
                        'ShowCam': show_cam,
                        'PricePerHour': price_in_vnd,
                        'SocialLink': self.social_link.value,
                        'Talent': self.talent.value,
                        'Games': self.games.value
                    }
                },
                upsert=True
            )
        
            # Prepare summary of registered information
            summary = f"Registration submitted for {name}. Your information has been stored:\n\n"
            summary += f"Duoer ID: {interaction.user.id}\n"
            summary += f"Name: {name}\n"
            summary += f"Birthday: {birthday}\n"
            summary += f"City: {city}\n"
            summary += f"Show Cam: {show_cam}\n"
            summary += f"Price per hour: {price_in_vnd // 1000}K VND\n"
            summary += f"Social Link: {self.social_link.value}\n"
            summary += f"Talents: {self.talent.value}\n"
            summary += f"Games: {self.games.value}\n"

            await interaction.response.send_message(summary)
        except PyMongoError as e:
            await interaction.response.send_message(f"A database error occurred: {str(e)}. Please try again or contact an administrator.")
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}. Please try again or contact an administrator.")
    
class AcceptDeclineView(nextcord.ui.View):
    def __init__(self, player_id, duoer_id, rent_hours, requested_start_time):
        super().__init__(timeout=None)
        self.player_id = player_id
        self.duoer_id = duoer_id
        self.rent_hours = rent_hours
        self.requested_start_time = requested_start_time

    @nextcord.ui.button(label="Accept", style=nextcord.ButtonStyle.green)
    async def accept(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if str(interaction.user.id) != str(self.duoer_id):
            await interaction.response.send_message("Only the duoer can accept this booking.", ephemeral=True)
            return

        actual_start_time = datetime.now()
        db = get_database_connection()
        try:
            result = db.Rentals.update_one(
                {
                    'PlayerID': self.player_id,
                    'DuoerID': self.duoer_id,
                    'RequestedStartTime': self.requested_start_time,
                    'Status': 'Pending'
                },
                {
                    '$set': {
                        'Status': 'Accepted',
                        'ActualStartTime': actual_start_time
                    }
                }
            )
        
            if result.modified_count > 0:
                # Start the timer when the booking is accepted
                await bot.rental_timer.start_timer(self.player_id, self.duoer_id, self.rent_hours, interaction.channel.id, actual_start_time)
            
                await interaction.response.send_message(f"Booking accepted! The countdown has started at {actual_start_time}.")
            else:
                await interaction.response.send_message("Unable to accept the booking. It may have been cancelled or already accepted.")
        except PyMongoError as err:
            await interaction.response.send_message(f"A database error occurred: {err}. Please try again or contact an administrator.")
    
        self.stop()

    @nextcord.ui.button(label="Decline", style=nextcord.ButtonStyle.red)
    async def decline(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if str(interaction.user.id) != str(self.duoer_id):
            await interaction.response.send_message("Only the duoer can decline this booking.", ephemeral=True)
            return

        db = get_database_connection()
        try:
            result = db.Rentals.update_one(
                {
                    'PlayerID': self.player_id,
                    'DuoerID': self.duoer_id,
                    'RequestedStartTime': self.requested_start_time,
                    'Status': 'Pending'
                },
                {
                    '$set': {
                        'Status': 'Declined'
                    }
                }
            )

            if result.modified_count > 0:
                decline_message = f"<@{self.player_id}> Your booking has been declined by the duoer."
                await interaction.response.send_message(decline_message)
            else:
                await interaction.response.send_message("Unable to decline the booking. It may have been cancelled or already processed.")
        except PyMongoError as err:
            await interaction.response.send_message(f"A database error occurred: {err}. Please try again or contact an administrator.")
        
        self.stop()

class RentalTimer:
    def __init__(self, bot):
        self.bot = bot
        self.active_rentals = {}
        self.check_rentals.start()

    async def start_timer(self, player_id, duoer_id, duration, channel_id, start_time):
        end_time = start_time + timedelta(hours=duration)
        self.active_rentals[(player_id, duoer_id)] = (end_time, channel_id, start_time)
        
        # Start the digital clock with End Early button
        await self.run_digital_clock(player_id, duoer_id, duration, channel_id, start_time)

    async def run_digital_clock(self, player_id, duoer_id, duration, channel_id, start_time):
        channel = self.bot.get_channel(channel_id)
        if channel:
            view = EndEarlyView(player_id, duoer_id, self)
            message = await channel.send("Rental time remaining: ", view=view)
            end_time = start_time + timedelta(hours=duration)
            
            while datetime.now() < end_time and (player_id, duoer_id) in self.active_rentals:
                time_left = end_time - datetime.now()
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                await message.edit(content=f"Rental time remaining: {hours:02d}:{minutes:02d}:{seconds:02d}", view=view)
                await asyncio.sleep(1)
            
            if (player_id, duoer_id) in self.active_rentals:
                await self.end_rental(player_id, duoer_id, end_time)
            await message.edit(content="Rental time has ended!", view=None)

    async def end_rental(self, player_id, duoer_id, end_time, ended_early=False):
        if (player_id, duoer_id) in self.active_rentals:
            _, channel_id, start_time = self.active_rentals[(player_id, duoer_id)]
            del self.active_rentals[(player_id, duoer_id)]
            
            actual_duration = (end_time - start_time).total_seconds() / 3600  # in hours
            
            await self.complete_rental(player_id, duoer_id, channel_id, end_time, actual_duration, ended_early)

    async def complete_rental(self, player_id, duoer_id, channel_id, end_time, actual_duration, ended_early):
        status = 'Ended Early' if ended_early else 'Completed'
        db = get_database_connection()
        try:
            result = db.Rentals.update_one(
                {
                    'PlayerID': player_id,
                    'DuoerID': duoer_id,
                    'Status': 'Accepted'
                },
                {
                    '$set': {
                        'Status': status,
                        'ActualEndTime': end_time,
                        'ActualDuration': actual_duration
                    }
                }
            )
    
            if result.modified_count == 0:
                print(f"No rental found to complete for player {player_id} and duoer {duoer_id}")
        except PyMongoError as err:
            print(f"A database error occurred: {err}")

        channel = self.bot.get_channel(channel_id)
        if channel:
            if ended_early:
                await channel.send(f"<@{player_id}> <@{duoer_id}> Rental has ended early. Total duration: {actual_duration:.2f} hours.")
            else:
                await channel.send(f"<@{player_id}> <@{duoer_id}> Rental has been completed. Total duration: {actual_duration:.2f} hours.")
                
    @tasks.loop(minutes=1)
    async def check_rentals(self):
        now = datetime.now()
        ended_rentals = []

        for (player_id, duoer_id), (end_time, channel_id, _) in self.active_rentals.items():
            if now >= end_time:
                ended_rentals.append((player_id, duoer_id))
                await self.end_rental(player_id, duoer_id, end_time, ended_early=False)

    def cog_unload(self):
        self.check_rentals.cancel()

class EndEarlyView(nextcord.ui.View):
    def __init__(self, player_id, duoer_id, rental_timer):
        super().__init__(timeout=None)
        self.player_id = player_id
        self.duoer_id = duoer_id
        self.rental_timer = rental_timer

    @nextcord.ui.button(label="End Early", style=nextcord.ButtonStyle.danger)
    async def end_early(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if str(interaction.user.id) != self.duoer_id:
            await interaction.response.send_message("Only the duoer can end the rental early.", ephemeral=True)
            return

        await self.rental_timer.end_rental(self.player_id, self.duoer_id, datetime.now(), ended_early=True)
        await interaction.response.send_message("Rental ended early.")
        self.stop()
        
# In your bot setup
bot.rental_timer = RentalTimer(bot)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    for guild in bot.guilds:
        print(f"Connected to guild: {guild.name} (id: {guild.id})")
        print(f"Member count: {guild.member_count}")

# Alive
app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
    print(f"Flask app is running on port {port}")

def keep_alive():
    def run():
        port = int(os.environ.get('PORT', 8080))
        app.run(host='0.0.0.0', port=port)
        print(f"Flask app is running on port {port}")
    
    server = Thread(target=run)
    server.start()
    print("Keep alive thread started")

# Call this function before running the bot
keep_alive()

# Run the bot
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
