import os
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from browser_use import Controller, ActionResult, Agent, Browser
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.browser.browser import BrowserConfig
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Load environment variables with comprehensive path checking
def find_and_load_env():
    """Find and load .env file from various possible locations"""

    # Define all possible .env locations
    script_dir = Path(__file__).parent
    project_root = script_dir.parent  # Go up one level from script directory

    env_locations = [
        Path('.env'),  # Current working directory
        script_dir / '.env',  # Same directory as script
        project_root / '.env',  # Parent directory (likely project root)
        Path('/home/usp/Application-Bot/.env'),  # Your specific path
        Path.cwd() / '.env',  # Current working directory (explicit)
        Path.home() / '.env',  # User home directory
    ]

    logger.info(f"🔍 Script location: {script_dir.absolute()}")
    logger.info(f"🔍 Project root: {project_root.absolute()}")
    logger.info(f"🔍 Current working directory: {Path.cwd().absolute()}")

    # Try each location
    for env_path in env_locations:
        abs_path = env_path.absolute()
        logger.debug(f"🔍 Checking: {abs_path}")

        if env_path.exists():
            try:
                load_dotenv(env_path)
                logger.info(f"✅ Successfully loaded .env from: {abs_path}")

                # Verify that variables were actually loaded
                test_vars = ['LINKEDIN_EMAIL', 'LINKEDIN_PASSWORD', 'OPENAI_API_KEY']
                loaded_count = sum(1 for var in test_vars if os.getenv(var))
                logger.info(f"✅ Loaded {loaded_count}/{len(test_vars)} key environment variables")

                return True
            except Exception as e:
                logger.warning(f"⚠️ Found .env at {abs_path} but failed to load: {e}")
                continue

    # If we get here, no .env file was found
    logger.error("❌ No .env file found in any expected location!")
    logger.error("📍 Searched locations:")
    for env_path in env_locations:
        exists = "✅ EXISTS" if env_path.exists() else "❌ NOT FOUND"
        logger.error(f"   - {env_path.absolute()} [{exists}]")

    return False


# Load environment variables
if not find_and_load_env():
    raise FileNotFoundError(
        "No .env file found. Please ensure .env file exists in one of the expected locations. "
        f"Your .env file should be at: /home/usp/Application-Bot/.env"
    )


@dataclass
class ApplicationStatus:
    """Data class to track application status"""
    job_title: str
    company: str
    job_url: str
    application_time: str
    status: str  # "success", "failed", "skipped"
    reason: str
    easy_apply: bool
    form_fields_filled: List[str]
    errors: List[str]


class LinkedInBotController:
    """Enhanced controller for LinkedIn automation"""

    def __init__(self):
        self.controller = Controller()
        self.session_data = {
            "start_time": datetime.now().isoformat(),
            "applications": [],
            "stats": {
                "total_jobs_checked": 0,
                "easy_apply_found": 0,
                "applications_submitted": 0,
                "applications_failed": 0,
                "jobs_skipped": 0
            }
        }
        self.setup_session_directories()
        self.user_intervention_start = None

    def setup_session_directories(self):
        """Create session directories for logging and data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = Path(f"./linkedin_sessions/{timestamp}")
        self.logs_dir = self.session_dir / "logs"
        self.data_dir = self.session_dir / "data"
        self.screenshots_dir = self.session_dir / "screenshots"

        for directory in [self.logs_dir, self.data_dir, self.screenshots_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        logger.info(f"Session directory created: {self.session_dir}")

    def register_actions(self):
        """Register all custom actions with the controller"""

        @self.controller.action("Get LinkedIn login credentials")
        def get_linkedin_credentials() -> ActionResult:
            """Returns LinkedIn email and password for login"""
            email = os.getenv("LINKEDIN_EMAIL")
            password = os.getenv("LINKEDIN_PASSWORD")

            if not email or not password:
                return ActionResult(
                    error="LinkedIn credentials not found in environment variables",
                    extracted_content=""
                )

            # Using sensitive data format for security
            credentials = f"Email: <secret>linkedin_email</secret>, Password: <secret>linkedin_password</secret>"
            return ActionResult(
                extracted_content=credentials,
                include_in_memory=True
            )

        @self.controller.action("Get user details for job applications")
        def get_user_details() -> ActionResult:
            """Returns comprehensive user details for filling job application forms"""

            user_info = {
                "personal": {
                    "first_name": os.getenv("USER_FIRST_NAME", ""),
                    "last_name": os.getenv("USER_LAST_NAME", ""),
                    "email": os.getenv("USER_EMAIL", ""),
                    "phone": os.getenv("USER_PHONE", ""),
                    "linkedin_url": os.getenv("USER_LINKEDIN_URL", ""),
                    "location": {
                        "city": os.getenv("USER_CITY", ""),
                        "state": os.getenv("USER_STATE", ""),
                        "country": os.getenv("USER_COUNTRY", ""),
                        "zip_code": os.getenv("USER_ZIP_CODE", "")
                    }
                },
                "professional": {
                    "current_title": os.getenv("USER_CURRENT_TITLE", ""),
                    "years_of_experience": "2",
                    "notice_period": "2 weeks",
                    "salary_expectation": os.getenv("USER_SALARY_EXPECTATION", ""),
                    "willing_to_relocate": "Yes",
                    "authorized_to_work": "Yes",
                    "require_sponsorship": "No"
                },
                "education": {
                    "degree": os.getenv("USER_DEGREE", ""),
                    "university": os.getenv("USER_UNIVERSITY", ""),
                    "graduation_year": os.getenv("USER_GRADUATION_YEAR", ""),
                    "gpa": os.getenv("USER_GPA", "")
                },
                "experience_responses": {
                    "have_experience": "Yes",
                    "years_experience": "2",
                    "familiar_with": "Yes",
                    "worked_with": "Yes",
                    "comfortable_with": "Yes"
                }
            }

            return ActionResult(
                extracted_content=json.dumps(user_info, indent=2),
                include_in_memory=True
            )

        @self.controller.action("Start user intervention timer for verification or OTP")
        def start_user_intervention_timer() -> ActionResult:
            """Starts a 2-minute timer for user intervention (OTP, captcha, etc.)"""
            self.user_intervention_start = datetime.now()
            logger.warning("🔔 USER INTERVENTION REQUIRED - You have 2 minutes to complete verification")
            logger.warning("🔔 Please complete the verification/OTP in the browser window")
            return ActionResult(
                extracted_content="Timer started - 2 minutes for user intervention",
                include_in_memory=True
            )

        @self.controller.action("Check if user intervention time exceeded")
        def check_user_intervention_timeout() -> ActionResult:
            """Checks if the 2-minute user intervention period has been exceeded"""
            if not self.user_intervention_start:
                return ActionResult(extracted_content="No intervention timer active")

            elapsed = datetime.now() - self.user_intervention_start
            if elapsed > timedelta(minutes=2):
                logger.error("❌ User intervention timeout exceeded (2 minutes)")
                return ActionResult(
                    extracted_content="TIMEOUT_EXCEEDED",
                    include_in_memory=True
                )
            else:
                remaining = 120 - elapsed.total_seconds()
                return ActionResult(
                    extracted_content=f"Timer active - {remaining:.0f} seconds remaining",
                    include_in_memory=True
                )

        @self.controller.action("Reset user intervention timer")
        def reset_user_intervention_timer() -> ActionResult:
            """Resets the user intervention timer after successful completion"""
            self.user_intervention_start = None
            logger.info("✅ User intervention completed successfully")
            return ActionResult(
                extracted_content="Timer reset - intervention completed",
                include_in_memory=True
            )

        @self.controller.action("Log job application attempt")
        def log_application_attempt(
                job_title: str,
                company: str,
                job_url: str,
                status: str,
                reason: str = "",
                easy_apply: bool = False,
                form_fields: str = "",
                errors: str = ""
        ) -> ActionResult:
            """Logs details of each job application attempt to JSON file"""

            try:
                application_data = ApplicationStatus(
                    job_title=job_title,
                    company=company,
                    job_url=job_url,
                    application_time=datetime.now().isoformat(),
                    status=status,
                    reason=reason,
                    easy_apply=easy_apply,
                    form_fields_filled=form_fields.split(",") if form_fields else [],
                    errors=errors.split(",") if errors else []
                )

                # Add to session data
                self.session_data["applications"].append(asdict(application_data))

                # Update stats
                self.session_data["stats"]["total_jobs_checked"] += 1
                if easy_apply:
                    self.session_data["stats"]["easy_apply_found"] += 1
                if status == "success":
                    self.session_data["stats"]["applications_submitted"] += 1
                elif status == "failed":
                    self.session_data["stats"]["applications_failed"] += 1
                elif status == "skipped":
                    self.session_data["stats"]["jobs_skipped"] += 1

                # Save to JSON file
                json_file = self.data_dir / "applications_log.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(self.session_data, f, indent=2, ensure_ascii=False)

                # Log summary
                stats = self.session_data["stats"]
                logger.info(f"📊 Stats - Checked: {stats['total_jobs_checked']}, "
                            f"Easy Apply: {stats['easy_apply_found']}, "
                            f"Applied: {stats['applications_submitted']}, "
                            f"Failed: {stats['applications_failed']}, "
                            f"Skipped: {stats['jobs_skipped']}")

                return ActionResult(
                    extracted_content=f"Application logged: {status} - {job_title} at {company}",
                    include_in_memory=True
                )

            except Exception as e:
                logger.error(f"Error logging application: {str(e)}")
                return ActionResult(
                    error=f"Failed to log application: {str(e)}",
                    extracted_content=""
                )

        @self.controller.action("Get current session statistics")
        def get_session_stats() -> ActionResult:
            """Returns current session statistics"""
            stats = self.session_data["stats"]
            elapsed_time = datetime.now() - datetime.fromisoformat(self.session_data["start_time"])

            summary = {
                "session_duration": str(elapsed_time).split(".")[0],  # Remove microseconds
                "statistics": stats,
                "success_rate": f"{(stats['applications_submitted'] / max(stats['total_jobs_checked'], 1) * 100):.1f}%",
                "easy_apply_rate": f"{(stats['easy_apply_found'] / max(stats['total_jobs_checked'], 1) * 100):.1f}%"
            }

            return ActionResult(
                extracted_content=json.dumps(summary, indent=2),
                include_in_memory=True
            )

        @self.controller.action("Check application time limit")
        def check_application_time_limit(start_time_iso: str) -> ActionResult:
            """Checks if too much time is being spent on a single application (5 minute limit)"""
            try:
                start_time = datetime.fromisoformat(start_time_iso)
                elapsed = datetime.now() - start_time

                if elapsed > timedelta(minutes=5):
                    return ActionResult(
                        extracted_content="TIME_LIMIT_EXCEEDED",
                        include_in_memory=True
                    )
                else:
                    remaining = 300 - elapsed.total_seconds()
                    return ActionResult(
                        extracted_content=f"Time remaining: {remaining:.0f} seconds",
                        include_in_memory=True
                    )
            except Exception as e:
                return ActionResult(
                    error=f"Error checking time limit: {str(e)}",
                    extracted_content=""
                )


class LinkedInEasyApplyBot:
    """Main LinkedIn Easy Apply automation bot"""

    def __init__(self):
        self.bot_controller = LinkedInBotController()
        self.bot_controller.register_actions()

        # Use minimal browser configuration
        self.browser_config = BrowserConfig(headless=False)

        # Initialize LLM
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=SecretStr(api_key),
            temperature=0.4
        )

        # Sensitive data for security
        self.sensitive_data = {
            'linkedin_email': os.getenv("LINKEDIN_EMAIL", ""),
            'linkedin_password': os.getenv("LINKEDIN_PASSWORD", "")
        }

    async def run(self):
        """Main execution method"""
        logger.info("🚀 Starting LinkedIn Easy Apply Bot")
        logger.info(f"📁 Session directory: {self.bot_controller.session_dir}")

        try:
            # Create and configure agent
            agent = Agent(
                task=self._get_main_task(),
                llm=self.llm,
                controller=self.bot_controller.controller,
                use_vision=True,
                save_conversation_path=str(self.bot_controller.logs_dir / "conversation"),
                sensitive_data=self.sensitive_data
            )

            # Run the automation
            await agent.run()

        except Exception as e:
            logger.error(f"❌ Bot execution failed: {str(e)}")
            raise
        finally:
            # Save final session data
            self._save_final_report()

    def _get_main_task(self) -> str:
        """Returns the comprehensive task instructions for the agent"""
        return """
You are a LinkedIn saved Job, Easy Apply automation bot. Follow this precise workflow:

## PHASE 1: LOGIN & SETUP
1. Navigate to linkedin.com
2. Call 'Get LinkedIn login credentials' and use ONLY those credentials to log in
3. If you encounter OTP, captcha, or "verify you're human" prompts:
   - Call 'Start user intervention timer' 
   - Wait and monitor for user completion
   - Every 30 seconds, call 'Check if user intervention time exceeded'
   - If TIMEOUT_EXCEEDED is returned, immediately quit the entire process
   - If user completes verification, call 'Reset user intervention timer' and continue
4. After successful login, navigate to the Jobs tab

## PHASE 2: SAVED JOBS PROCESSING
1. In LinkedIN, Navigate to "Jobs -> My Jobs" -> "Saved Jobs or Saved". Don't go to In progress or others. The exact link is: "https://www.linkedin.com/my-items/saved-jobs/?cardType=SAVED"
2. For each saved job, follow this loop:

   **Job Analysis Phase:**
   - Open the job posting (keep the same browser tab)
   - Record the job title and company name
   - Check if it has "Easy Apply" button (look for blue "Easy Apply" button). Easy Apply is different from Apply. And you only do "Easy Apply".
   - Call 'Log job application attempt' tool with initial status

   **Easy Apply Processing:**
   - If NO Easy Apply: Log as "skipped" with reason "not_easy_apply", come back to "https://www.linkedin.com/my-items/saved-jobs/?cardType=SAVED" and move to next job. "Apply" button is different from the Easy Apply Button we're talking about
   - If YES Easy Apply: Click the "Easy Apply" button and proceed to application

   **Application Form Handling:**
   - Record start time for the application
   - Every 2 minutes, call 'Check application time limit' with start time
   - If TIME_LIMIT_EXCEEDED returned, abandon this application and move to next
   - Leave the default resume selected (don't change it)
   - Fill ALL form fields using data from 'Get user details for job applications':
     * Use personal info for contact fields
     * For experience questions: ALWAYS answer "Yes" 
     * For "years of experience" fields: ALWAYS enter "2"
     * For location fields: Use location data from user details
     * For salary expectations: Use provided salary or leave blank
     * For "willing to relocate": Answer "Yes"
     * For work authorization: Answer "Yes"
     * For sponsorship required: Answer "No"
     * For US citizenship: Answer "No"
   - If form has multiple pages, fill each page completely before proceeding
   - After filling all the fields, you'll be at a 'Review' page, where you need to scroll all the way down until you see the submit button.
   - Successful Application is when you hit the submit button, not just the save button.
   - Review all fields before final submission
   - Submit the application

   **Post-Application Logging:**
   - Call 'Log job application attempt' with comprehensive details:
     * Status: "success" if submitted, "failed" if error occurred
     * Include all form fields that were filled
     * Include any errors encountered
   - Navigate back to saved jobs list
   - Continue to next job

**Important: If a new tab opens up due to anything, just close it and come back to https://www.linkedin.com/my-items/saved-jobs/?cardType=SAVED
**Scroll down to see all buttons if you can't find the right buttons at any point.

## PHASE 3: CONTINUOUS OPERATION
- Process ALL saved jobs in the list
- Call 'Get current session statistics' every 10 jobs to track progress
- Maintain the same browser tab throughout (don't open new tabs)
- If any error occurs, log it and continue to next job
- Never spend more than 5 minutes on a single application

## ERROR HANDLING RULES
- For captcha/verification: Use user intervention timer (2 min max)
- For application errors: Log and skip to next job
- For network errors: Wait 30 seconds and retry once
- For timeout: Skip current job and continue
- NEVER create fake information - only use provided user details

## COMPLETION
Continue processing until all saved jobs are checked or user intervention timeout occurs.
Call 'Get current session statistics' at the end for final summary.

Remember: Keep the LinkedIn tab open throughout the entire process and maintain session continuity.
"""

    def _save_final_report(self):
        """Save final session report"""
        try:
            report_file = self.bot_controller.data_dir / "final_report.json"
            final_report = {
                "session_summary": self.bot_controller.session_data,
                "end_time": datetime.now().isoformat(),
                "total_runtime": str(datetime.now() - datetime.fromisoformat(
                    self.bot_controller.session_data["start_time"]
                )).split(".")[0]
            }

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(final_report, f, indent=2, ensure_ascii=False)

            logger.info(f"📊 Final report saved: {report_file}")
            logger.info(f"🎯 Session completed - Check {self.bot_controller.session_dir} for all data")

        except Exception as e:
            logger.error(f"Error saving final report: {str(e)}")


# Environment variables setup helper
def create_env_template():
    """Creates a .env template file with required variables"""
    env_template = """
# LinkedIn Credentials (REQUIRED)
LINKEDIN_EMAIL=your_linkedin_email@example.com
LINKEDIN_PASSWORD=your_linkedin_password

# OpenAI API Key (REQUIRED)
OPENAI_API_KEY=your_openai_api_key

# User Details for Applications
USER_FIRST_NAME=Your First Name
USER_LAST_NAME=Your Last Name
USER_EMAIL=your_email@example.com
USER_PHONE=+1234567890
USER_LINKEDIN_URL=https://linkedin.com/in/yourprofile
USER_CITY=Your City
USER_STATE=Your State
USER_COUNTRY=Your Country
USER_ZIP_CODE=12345
USER_CURRENT_TITLE=Your Current Job Title
USER_SALARY_EXPECTATION=80000
USER_DEGREE=Your Degree
USER_UNIVERSITY=Your University
USER_GRADUATION_YEAR=2020
USER_GPA=3.5
"""

    with open('.env.template', 'w') as f:
        f.write(env_template.strip())

    print("📝 Created .env.template - Please copy to .env and fill in your details")


async def main():
    """Main execution function"""
    try:
        # The .env file has already been loaded at module level
        # Just validate that the required variables are available

        logger.info(f"🔍 Current working directory: {Path.cwd()}")
        logger.info(f"🔍 Script location: {Path(__file__).parent}")

        # Validate required environment variables with detailed feedback
        required_vars = ['LINKEDIN_EMAIL', 'LINKEDIN_PASSWORD', 'OPENAI_API_KEY']
        missing_vars = []
        empty_vars = []
        template_vars = []

        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_vars.append(var)
            elif value.strip() == "":
                empty_vars.append(var)
            elif (value.startswith('your_') or
                  'example.com' in value.lower() or
                  value in ['your_linkedin_email@example.com', 'your_linkedin_password', 'your_openai_api_key']):
                template_vars.append(var)

        # Report issues with detailed feedback
        all_issues = []
        if missing_vars:
            all_issues.extend(missing_vars)
            logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")

        if empty_vars:
            all_issues.extend(empty_vars)
            logger.error(f"❌ Empty environment variables: {', '.join(empty_vars)}")

        if template_vars:
            all_issues.extend(template_vars)
            logger.error(f"❌ Template values still present: {', '.join(template_vars)}")

        if all_issues:
            logger.error("🔧 Please update your .env file with actual values")
            logger.info("💡 Your .env file was found and loaded, but some variables need to be set")
            logger.info(f"📁 .env file location: /home/usp/Application-Bot/.env")

            # Show what we found vs what we need
            logger.info("📋 Environment variable status:")
            for var in required_vars:
                value = os.getenv(var)
                if value and var not in all_issues:
                    # Mask the value for security
                    if 'PASSWORD' in var:
                        masked = '*' * min(len(value), 8)
                    elif 'API_KEY' in var:
                        masked = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "sk-****"
                    elif 'EMAIL' in var:
                        if '@' in value:
                            parts = value.split('@')
                            masked = f"{parts[0][:2]}***@{parts[1]}"
                        else:
                            masked = f"{value[:3]}***"
                    else:
                        masked = f"{value[:10]}..."

                    logger.info(f"   ✅ {var}: {masked}")
                else:
                    logger.error(
                        f"   ❌ {var}: {'MISSING' if var in missing_vars else 'EMPTY' if var in empty_vars else 'TEMPLATE VALUE'}")

            return

        # Log successful credential detection (without exposing values)
        logger.info("✅ All required credentials loaded successfully")
        linkedin_email = os.getenv('LINKEDIN_EMAIL')
        openai_key = os.getenv('OPENAI_API_KEY')

        if linkedin_email:
            if '@' in linkedin_email:
                parts = linkedin_email.split('@')
                masked_email = f"{parts[0][:2]}***@{parts[1]}"
            else:
                masked_email = f"{linkedin_email[:3]}***"
            logger.info(f"📧 LinkedIn email: {masked_email}")

        if openai_key and len(openai_key) > 12:
            masked_key = f"{openai_key[:8]}...{openai_key[-4:]}"
            logger.info(f"🔑 OpenAI key: {masked_key}")

        # Initialize and run bot
        bot = LinkedInEasyApplyBot()
        await bot.run()

    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {str(e)}")
        logger.error(f"🔍 Current directory: {Path.cwd()}")
        logger.error(f"🔍 .env file exists at expected location: {Path('/home/usp/Application-Bot/.env').exists()}")
        raise


if __name__ == "__main__":
    # Print startup banner
    print("🤖 LinkedIn Easy Apply Bot v2.0")
    print("=" * 50)
    print("🎯 Features:")
    print("  • Automatic LinkedIn login with credential protection")
    print("  • Smart OTP/captcha handling with user intervention")
    print("  • Easy Apply job detection and application")
    print("  • Comprehensive logging and statistics")
    print("  • Session persistence and error recovery")
    print("  • Time limits and safety controls")
    print("=" * 50)

    asyncio.run(main())