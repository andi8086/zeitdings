#!/bin/python
# encoding: utf-8

import os, sys
import sqlite3
import npyscreen

class Database:
    work_db = None
    projects_db = None

    def __init__(self):
        self.work_db = sqlite3.connect("work.db")
        cursor = self.work_db.cursor()

        sql_query = """
CREATE TABLE IF NOT EXISTS times(
pkID INTEGER PRIMARY KEY AUTOINCREMENT,
date TEXT,
hours REAL,
project INTEGER,
desc TEXT);
"""
        cursor.execute(sql_query)
        self.work_db.commit()

        sql_query = """
CREATE TABLE IF NOT EXISTS projects(
pkID INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT);
"""
        cursor.execute(sql_query)
        self.work_db.commit()

    def reopen(self):
        self.work_db.close()
        self.work_db = sqlite3.connect("work.db")

    def get_projects(self):
        sql_query = "SELECT * FROM `projects` WHERE 1;"
        cursor = self.work_db.cursor()
        cursor.execute(sql_query)
        return list(cursor.fetchall())

    def add_project(self, name):
        sql_query = "INSERT INTO `projects` (name) VALUES ('{}')".format(name)
        cursor = self.work_db.cursor()
        cursor.execute(sql_query)
        self.work_db.commit()

    def insert_time(self, date, project, desc, hours):
        sql_query = "INSERT INTO `times` (date, hours, project, desc) \
            VALUES('{}', {}, {}, '{}')".format(date, hours, project, desc)
        cursor = self.work_db.cursor()
        cursor.execute(sql_query)
        self.work_db.commit()

    def get_time_entries(self):
        sql_query = """SELECT times.pkID, times.date, projects.name, times.desc,
times.hours FROM `times` INNER JOIN `projects` ON projects.pkID = times.project;
"""
        cursor = self.work_db.cursor()
        cursor.execute(sql_query)
        return list(cursor.fetchall())

    def delete_entry(self, pkid):
        sql_query = "DELETE FROM times WHERE pkID = {};".format(pkid)
        cursor = self.work_db.cursor()
        cursor.execute(sql_query)
        self.work_db.commit()

    def check_project_id_unused(self, pkid):
        sql_query = "SELECT times.pkID FROM `times` WHERE times.project = {};"\
            .format(pkid)
        cursor = self.work_db.cursor()
        cursor.execute(sql_query)
        return len(cursor.fetchall()) == 0

    def delete_project(self, pkid):
        sql_query = "DELETE FROM projects WHERE pkID = {};".format(pkid)
        cursor = self.work_db.cursor()
        cursor.execute(sql_query)
        self.work_db.commit()

    def conv_line(self, t):
        return "%s, %s, %.2f" % (t[0], t[1], t[2])

    def get_project_report(self, pkid):
        sql_query = "SELECT sum(times.hours) FROM `times` \
WHERE times.project = {};".format(pkid)
        cursor = self.work_db.cursor()
        cursor.execute(sql_query)
        total_hours = float(cursor.fetchall()[0][0])

        sql_query = "SELECT times.date, times.desc, times.hours \
FROM `times` WHERE times.project = {};".format(pkid)
        cursor = self.work_db.cursor()
        cursor.execute(sql_query)
        return ("Total hours: %.2f\n" % total_hours) + \
            "\n".join(self.conv_line(e) for e in cursor.fetchall())

    def dump_all(self):
        sql_query = """SELECT times.pkID, times.date, projects.name, times.hours
FROM `times` INNER JOIN `projects` ON projects.pkID = times.project;
"""
        cursor = self.work_db.cursor()
        cursor.execute(sql_query)
        print(list(cursor.fetchall()))

    def __del__(self):
        self.work_db.close()


class NewProjectForm(npyscreen.ActionForm):
    def create(self):
        self.value = None
        self.wgProjectName = self.add(npyscreen.TitleText,
            name = "Project Name:")

    def on_ok(self):
        self.parentApp.database.add_project(self.wgProjectName.value)
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()


class DeleteProjectForm(npyscreen.ActionForm):
    def create(self):
        self.value = None
        self.project = self.add(npyscreen.TitleCombo, name = "Project: ")

    def beforeEditing(self):
        self.projects = self.parentApp.database.get_projects()
        self.project.values = [p[1] for p in self.projects]

    def on_ok(self):
        if self.project.value == None:
            self.parentApp.invalid_input_msg("No project selected")
            return

        project_id = self.projects[self.project.value][0]

        if not self.parentApp.database.check_project_id_unused(project_id):
            self.parentApp.error_msg("Cannot delete referenced projects! \
Delete referencing time entries first.")
            return

        self.parentApp.database.delete_project(project_id)
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()


class ProjectReportForm(npyscreen.ActionForm):
    def create(self):
        self.value = None
        self.project = self.add(npyscreen.TitleCombo, name = "Project: ")

    def beforeEditing(self):
        self.projects = self.parentApp.database.get_projects()
        self.project.values = [p[1] for p in self.projects]

    def on_ok(self):
        if self.project.value == None:
            self.parentApp.invalid_input_msg("No project selected")
            return

        project_id = self.projects[self.project.value][0]

        if self.parentApp.database.check_project_id_unused(project_id):
            self.parentApp.error_msg(
                "There are no times booked on this project!")
            return

        report = self.parentApp.database.get_project_report(project_id)
        npyscreen.notify_confirm(report, "Report")

        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()


class TimeEntryForm(npyscreen.ActionForm):

    def create(self):
        self.date = self.add(npyscreen.TitleDateCombo, name = "Date: ")
        self.project = self.add(npyscreen.TitleCombo, name = "Project: ")
        self.desc = self.add(npyscreen.TitleText, name = "Description: ")
        self.hours = self.add(npyscreen.TitleText, name = "Hours: ")

    def beforeEditing(self):
        self.projects = self.parentApp.database.get_projects()
        self.project.values = [p[1] for p in self.projects]

    def on_ok(self):
        if self.project.value == None:
            self.parentApp.invalid_input_msg("No project selected")
            return

        f_hours = 0.0
        try:
            f_hours = float(self.hours.value)
        except ValueError:
            self.parentApp.invalid_input_msg(
                "Hours must be floating point value")
            self.hours.value = None
            return

        project_id = self.projects[self.project.value][0]
        self.parentApp.database.insert_time(self.date.value, project_id,
            self.desc.value, f_hours)
        self.parentApp.switchFormPrevious()

    def on_cancel(self):
        self.parentApp.switchFormPrevious()

HELP_MSG = """
    Zeitdings, Version 0.1
    (L)CopyLeft Andreas J. Reichel 2021
    -
    Key bindings:
        ^T: Add time entry
        T: delete time entry
        -----------------------------
        ^P: Add project
        P:  delete project
        -----------------------------
        ^R: Generate project report
        -----------------------------
        ^H: Show this help screen
        ^X: Quit
"""


class RecordList(npyscreen.MultiLineAction):
    def __init__(self, *args, **keywords):
        super(RecordList, self).__init__(*args, **keywords)
        self.add_handlers({
            "^T": self.when_add_timeentry,
            "^P": self.when_add_project,
            "P": self.when_delete_project,
            "^X": self.when_exit,
            "T": self.when_delete_entry,
            "^R": self.when_project_report,
            "^H": self.when_help
            })

    def display_value(self, vl):
        return "%s  |  %s  |  %s  |  %.2f" % (vl[1], vl[2], vl[3], vl[4])

    def actionHighlighted(self, act_on_this, keypress):
        # self.parent.parentApp.getForm('asfsef').value = act_on_this[0]
        pass

    def when_help(self, *args, **keywords):
        npyscreen.notify_confirm(HELP_MSG, "Help")

    def when_add_timeentry(self, *args, **keywords):
        self.parent.parentApp.getForm("TIMEENTRY").value = None
        self.parent.parentApp.switchForm("TIMEENTRY")

    def when_add_project(self, *args, **keywords):
        self.parent.parentApp.getForm("NEWPROJECT").value = None
        self.parent.parentApp.switchForm("NEWPROJECT")

    def when_exit(self, *args, **keywords):
        self.parent.parentApp.switchForm(None)

    def when_delete_entry(self, *args, **keywords):
        self.parent.parentApp.database.delete_entry(self.values[self.cursor_line][0])
        # reload form by switching to the same again
        self.parent.parentApp.switchForm("MAIN")

    def when_delete_project(self, *args, **keywords):
        self.parent.parentApp.switchForm("DELETEPROJECT")

    def when_project_report(self, *args, **keywords):
        self.parent.parentApp.switchForm("PROJECTREPORT")


class MainForm(npyscreen.FormMutt):
    MAIN_WIDGET_CLASS = RecordList
    def beforeEditing(self):
        self.update_list()

    def update_list(self):
        self.wMain.values = self.parentApp.database.get_time_entries()
        self.wMain.display()


class TestApp(npyscreen.NPSAppManaged):

    def onStart(self):
        self.database = Database()
        self.addForm("MAIN", MainForm)
        self.addForm("TIMEENTRY", TimeEntryForm)
        self.addForm("NEWPROJECT", NewProjectForm)
        self.addForm("DELETEPROJECT", DeleteProjectForm)
        self.addForm("PROJECTREPORT", ProjectReportForm)

    def invalid_input_msg(self, msg):
        npyscreen.notify_confirm(msg, 'Invalid Input')

    def error_msg(self, msg):
        npyscreen.notify_confirm(msg, 'Error')


if __name__ == "__main__":
    App = TestApp()
    App.run()
