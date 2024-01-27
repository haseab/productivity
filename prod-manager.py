
import time
from datetime import date, datetime, timedelta
from http.client import RemoteDisconnected
from socket import gaierror, timeout

import pandas as pd
import requests
from gcsa.google_calendar import GoogleCalendar
from todoist_api_python.api import TodoistAPI

import os
from dotenv import load_dotenv

# Load the environment variables from .env file
load_dotenv()

class ProdManager():
    def __init__(self):
        self.cal_pushover = {
            "token": os.getenv("CAL_PUSHOVER_TOKEN"),
            "user": os.getenv("CAL_PUSHOVER_USER"),
            "message": ".",
            "title": "Whitespace!",
            "sound": "bike"
        }
        self.todo_inbox_pushover = {
            "token": os.getenv("TODO_INBOX_PUSHOVER_TOKEN"),
            "user": os.getenv("TODO_INBOX_PUSHOVER_USER"),
            "title": "Sort Todoist Inbox!", 
            "message": ".",
            "sound": "siren"
        }
        self.todo_due_pushover = {
            "token": os.getenv("TODO_DUE_PUSHOVER_TOKEN"),
            "user": os.getenv("TODO_DUE_PUSHOVER_USER"),
            "title": "Overdue Todoist Tasks!",
            "message": ".",
            "sound": "gamelan"
        }
        self.business = GoogleCalendar(os.getenv("BUSINESS_CALENDAR_ID"))
        self.maintenance = GoogleCalendar(os.getenv("MAINTENANCE_CALENDAR_ID"))
        self.sprints = GoogleCalendar(os.getenv("SPRINTS_CALENDAR_ID"))
        self.adhoc = GoogleCalendar(os.getenv("ADHOC_CALENDAR_ID"))
        self.food = GoogleCalendar(os.getenv("FOOD_CALENDAR_ID"))
        self.habits = GoogleCalendar(os.getenv("HABITS_CALENDAR_ID"))
        self.projects = GoogleCalendar(os.getenv("PROJECTS_CALENDAR_ID"))
        self.social = GoogleCalendar(os.getenv("SOCIAL_CALENDAR_ID"))
        self.technicalities = GoogleCalendar(os.getenv("TECHNICALITIES_CALENDAR_ID"))
        self.understanding = GoogleCalendar(os.getenv("UNDERSTANDING_CALENDAR_ID"))
        self.fptstudio = GoogleCalendar(os.getenv("FPTSTUDIO_CALENDAR_ID"))
        
    def sleep(self, seconds, divisor=4):
        print(f"Sleeping for {seconds} seconds")
        import time
        for i in range(seconds*divisor):
            time.sleep(seconds/(seconds*divisor))

    def create_calendar_dic(self):
        calendar_list = [self.business, self.maintenance, self.sprints, self.adhoc, self.habits, self.projects, self.social, self.technicalities, self.understanding, self.fptstudio]
        string_list = ["Business", "Maintenance", "Sprints", "Ad-Hoc", "Gradual Habits", "Projects", "Social", "Technicalities", "Understanding", "fpt-studio"]
        cal_dic = {}
        for string, cal in zip(string_list, calendar_list):
            cal_dic[string] = cal
        return cal_dic

    def get_all_current_events(self, cal_dic):
        date_before = datetime.now().astimezone()
        date_after = datetime.now().astimezone() + timedelta(minutes=0.5)
        all_events = []
        
        for name, calendar in cal_dic.items():
            events = list(calendar.get_events(date_before, date_after, single_events=True))
            if events != []:
                events += [name]
                all_events += [events]
        return all_events

    def run_ifttt(self):
        event_name = "whitespace"
        resp = requests.post(f"https://maker.ifttt.com/trigger/{event_name}/with/key/{self.ifttt_webhooks_key}")
        
    def check_whitespace(self):
        print('checking for whitespace...')
        all_events = self.get_all_current_events(cal_dic)
        self.all_event_names = [event_group[0].summary for event_group in all_events]
        count =0
        for event_group in all_events:
            print(event_group)
            event = event_group[0]
            now = datetime.now().astimezone()
            print("TYPES: ", type(event.end), type(event.start))
            if type(event.end) != date and type(event.start) != date:
                if event.end != None and now + timedelta(minutes=5) < event.end and now > event.start:
                    count +=1

        if count == 0:
            requests.post("https://api.pushover.net/1/messages.json", json=self.cal_pushover)
            print(datetime.now().astimezone())
            print('Failed! No Event Happening Right Now!!!')
            print(all_events)
            print("sent pushover notification")
        else:
            print(datetime.now().astimezone())
            print('Passed! Event Happening Right Now!!!')
            print(all_events)

    def check_empty_inbox(self, df_tasks, projects):

        print("checking todoist inbox...")
        inbox_id = [project['id'] for project in projects if project['name'] == 'Inbox'][0]

        inbox = df_tasks[(df_tasks['project_id'] == inbox_id) & (df_tasks['section_id'] != '68959271')]
        
        if len(inbox) != 0:
            print()
            print("TODOIST INBOX NON EMPTY!!")
            print("sent pushover notification")
            print()
            resp = requests.post("https://api.pushover.net/1/messages.json", json=self.todo_inbox_pushover)
        return df_tasks[['content', 'project_id', 'section_id', 'url', 'parent_id']]
    
    def check_empty_due_today(self, df_tasks):
        print("checking todoist due today...")
        today = pd.Timestamp(datetime.utcnow())
        today = today.tz_localize('UTC')
        tasks_due = df_tasks[df_tasks["due"].notnull()]
        tasks_due_nr = tasks_due[[True if "datetime" in obj else False for obj in tasks_due["due"].values]].copy()
        tasks_due_nr['due'] = [obj['datetime'] for obj in tasks_due_nr['due'].values]
        tasks_due_nr['due'] = [dt + "Z" if dt[-1] != "Z" else dt for dt in tasks_due_nr['due'].values ]
        tasks_due_nr['due'] = pd.to_datetime(tasks_due_nr['due'], utc=True)
        past_due = tasks_due_nr[tasks_due_nr['due'] < today]

        count = 0
        for task in past_due['content'].values:
            print(task)
            if task not in self.all_event_names:
                count +=1
        if count >= 1:
            print()
            print("DIDN'T CHECK OFF COMPLETED ITEMS!!")
            print("send pushover notification")
            print()
            resp = requests.post("https://api.pushover.net/1/messages.json", json=self.todo_due_pushover)
            return

    def check_todoist(self):
        print("checking todoist...")
        print("getting tasks...")
        tasks = requests.get("https://api.todoist.com/rest/v2/tasks", headers={'Authorization':f"Bearer {os.getenv('TODOIST_API_KEY')}"}).json()
        projects = requests.get("https://api.todoist.com/rest/v2/projects", headers={'Authorization':f"Bearer {os.getenv('TODOIST_API_KEY')}"}).json()
        df_tasks = pd.DataFrame(tasks)
        self.check_empty_inbox(df_tasks, projects)
        self.check_empty_due_today(df_tasks)
        return
    

    def run_manager(self):
        started = False
        count = 0
        backoff_time = 300  # Initial backoff time in seconds
        max_backoff_time = 4800  # Maximum backoff time in seconds

        print("STARTING PROD MANAGER")
        while True:
            now = datetime.now()
            if now.hour < 8 or now.hour >= 22:
                print()
                print("=======NIGHT HOURS=======")
                print()
                self.sleep(300)
                continue
            try:
                self.check_whitespace()
                if started == False:
                    self.check_todoist()
                    started = True
                self.sleep(300)
                count += 1 
                if count >= 12:
                    self.check_todoist()
                    count = 0
                backoff_time = 1  # Reset backoff time after a successful request

            # except (ConnectionAbortedError, ConnectionResetError, TimeoutError, RemoteDisconnected, gaierror, timeout, requests.exceptions.HTTPError) as e:
            except:
                print("CONNECTION ABORTED")
                print("RESTARTING.....")
                start = time.perf_counter()
                self.sleep(backoff_time)
                print(f'Done Restarting after {time.perf_counter() - start} seconds')

                backoff_time = min(backoff_time * 2, max_backoff_time)  # Exponential backoff with a maximum limit


if __name__ == "__main__":
    pm = ProdManager()
    cal_dic = pm.create_calendar_dic()  
    pm.run_manager()
    # pm.check_empty_inbox()
