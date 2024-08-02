CREATE DATABASE BotDiscord;
-- Create Players table
CREATE TABLE Players (
    PlayerID VARCHAR(20) PRIMARY KEY,
    PlayerName VARCHAR(100) NOT NULL,
    RegistrationDate DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create Duoers table
CREATE TABLE Duoers (
    DuoerID VARCHAR(20) PRIMARY KEY,
    DuoerName VARCHAR(100) NOT NULL,
    Birthday DATE,
    City VARCHAR(100),
    ShowCam ENUM('yes', 'no') DEFAULT 'no',
    PricePerHour INT NOT NULL,
    SocialLink VARCHAR(255),
    Talent TEXT,
    Games TEXT,
    RegistrationDate DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create Rentals table
CREATE TABLE Rentals (
    RentalID INT AUTO_INCREMENT PRIMARY KEY,
    PlayerID VARCHAR(20),
    DuoerID VARCHAR(20),
    RequestedStartTime DATETIME NOT NULL,
    RequestedDuration DECIMAL(5,2) NOT NULL,
    TotalPrice INT NOT NULL,
    Status ENUM('Pending', 'Accepted', 'Declined', 'Completed', 'Ended Early') DEFAULT 'Pending',
    ActualStartTime DATETIME,
    ActualEndTime DATETIME,
    ActualDuration DECIMAL(5,2),
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (PlayerID) REFERENCES Players(PlayerID),
    FOREIGN KEY (DuoerID) REFERENCES Duoers(DuoerID)
);