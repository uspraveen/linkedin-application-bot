# 🤖 LinkedIn Easy Apply Agent v2.0

An intelligent, production-ready automation bot that applies to LinkedIn Easy Apply jobs with advanced security, logging, and error handling.


## 📽 Watch it in Work:

[![Watch the demo](https://img.youtube.com/vi/ITDgc9iQodI/0.jpg)](https://www.youtube.com/watch?v=ITDgc9iQodI)




## 🌟 Features

### 🔐 **Security & Safety**
- **Credential Protection**: Uses environment variables and sensitive data handling
- **Domain Restriction**: Only allows LinkedIn domains to prevent security issues
- **User Intervention**: Handles OTP/captcha with 2-minute user intervention windows
- **Time Limits**: Prevents getting stuck on single applications (5-minute limit per job)

### 🎯 **Smart Automation**
- **Easy Apply Detection**: Automatically identifies and processes only Easy Apply jobs
- **Form Intelligence**: Uses GPT-4o to understand and fill complex application forms
- **Resume Management**: Keeps default resume selection (no file uploads needed)
- **Experience Handling**: Automatically answers experience questions with "Yes" and "2 years"

### 📊 **Comprehensive Logging**
- **Real-time Statistics**: Tracks applications, success rates, and performance metrics
- **Session Persistence**: Maintains data across browser sessions
- **JSON Logging**: Structured data for easy analysis and reporting
- **Error Tracking**: Detailed error logging with recovery mechanisms

### 🧠 **Advanced AI Integration**
- **Vision-enabled**: Uses computer vision to understand page layouts
- **Natural Language**: Processes form questions intelligently
- **Context Awareness**: Maintains context throughout the automation process
- **Adaptive Behavior**: Adjusts to different job application forms dynamically

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the bot files
git clone <repository-url>
cd linkedin-easy-apply-bot

# Run setup script
python setup.py
```

### 2. Configuration

Copy the template and add your credentials:

```bash
cp .env.template .env
nano .env  # Edit with your details
```

Required credentials in `.env`:
```env
# LinkedIn Credentials
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password

# OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key

# Your Details (for applications)
USER_FIRST_NAME=John
USER_LAST_NAME=Doe
USER_EMAIL=john.doe@example.com
USER_PHONE=+1234567890
# ... (see .env.template for all fields)
```

### 3. Run the Bot

```bash
python linkedin_bot.py
```

## 📋 How It Works

### Phase 1: Login & Setup
1. **Secure Login**: Uses your credentials to log into LinkedIn
2. **OTP Handling**: Detects verification requirements and waits for user input
3. **Session Management**: Maintains login state throughout the process

### Phase 2: Job Processing
1. **Navigation**: Goes to "My Jobs" → "Saved Jobs"
2. **Detection**: Identifies Easy Apply jobs vs. external applications
3. **Application**: Fills forms using your provided information
4. **Logging**: Records every attempt with detailed metadata

### Phase 3: Continuous Operation
1. **Loop Processing**: Handles all saved jobs sequentially
2. **Error Recovery**: Continues processing even if individual jobs fail
3. **Statistics**: Provides real-time progress updates

## 📊 Output & Logging

### Session Directory Structure
```
linkedin_sessions/YYYYMMDD_HHMMSS/
├── data/
│   ├── applications_log.json      # Detailed application logs
│   └── final_report.json          # Session summary
├── logs/
│   ├── conversation/              # AI conversation logs
│   └── linkedin_bot
