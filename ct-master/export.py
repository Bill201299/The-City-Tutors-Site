import shutil
import sqlite3
from datetime import date, datetime
import os
from pandas import read_sql_query

def export():
    # Longer SQL Statements
    totals = """SELECT
                    COUNT(CASE WHEN account_type_id = 4 THEN 1 END) AS 'Total Tutor Profiles',
                    COUNT(CASE WHEN account_type_id IN (1,2,3) THEN 1 END) AS 'Total Student Profiles',
                    COUNT(*)
                FROM tutor_profile;"""

    tutorinfo = """SELECT p.id,
                       p.full_name as "Full Name",
                       p.nickname,
                       p.phone_number as "Phone Number",
                       p.tutee_contact as "Contact Info",
                       p.offered_hours as "Offered Hours",
                       TOTAL(m.stop_datetime IS NOT NULL) as "Tutoring Sessions",
                       bc.status as "Background Check",
                       CASE WHEN (o3.completed IS NOT NULL AND
                                  o4.completed IS NOT NULL AND
                                  o9.completed IS NOT NULL AND
                                  o11.completed )
                            THEN 'Done'
                            ELSE 'Incomplete'
                        END as "Orientation Status",
                       max(
                            max(coalesce(o3.completed, 0)),
                            max(coalesce(o4.completed, 0)),
                            max(coalesce(o9.completed, 0)),
                            max(coalesce(o11.completed, 0))
                       ) as "Last Completed Date",
                       o1.completed,
                       o2.completed,
                       o3.completed,
                       o4.completed,
                       o5.completed,
                       o6.completed,
                       o7.completed,
                       o8.completed,
                       o9.completed,
                       o10.completed,
                       o11.completed
                    FROM tutor_profile p
                    LEFT JOIN tutor_orientation1 o1 on p.user_id = o1.user_id
                    LEFT JOIN tutor_orientation2 o2 on p.user_id = o2.user_id
                    LEFT JOIN tutor_orientation3 o3 on p.user_id = o3.user_id
                    LEFT JOIN tutor_orientation4 o4 on p.user_id = o4.user_id
                    LEFT JOIN tutor_orientation5 o5 on p.user_id = o5.user_id
                    LEFT JOIN tutor_orientation6 o6 on p.user_id = o6.user_id
                    LEFT JOIN tutor_orientation7 o7 on p.user_id = o7.user_id
                    LEFT JOIN tutor_orientation8 o8 on p.user_id = o8.user_id
                    LEFT JOIN tutor_orientation9 o9 on p.user_id = o9.user_id
                    LEFT JOIN tutor_orientation10 o10 on p.user_id = o10.user_id
                    LEFT JOIN tutor_orientation11 o11 on p.user_id = o11.user_id
                    LEFT JOIN tutor_backgroundcheckrequest bc on p.user_id = bc.user_id
                    LEFT JOIN tutor_meetingmembership tmm on p.user_id = tmm.user_id
                    LEFT JOIN tutor_meeting m on tmm.meeting_id = m.id
                    WHERE account_type_id = 4
                    GROUP BY p.user_id, p.full_name
                    ORDER BY "Orientation Status", p.full_name;"""

    studentinfo = """SELECT s.account_type_id,
                       s.id,
                       s.full_name as "Full Name",
                       s.nickname,
                       s.parent_or_guardian_name,
                       s.phone_number as "Phone Number",
                       tg.display as "Grade",
                       s.tutoring_reason
                    FROM tutor_profile s
                    LEFT JOIN tutor_gradelevel tg on s.grade_level_id = tg.id
                    WHERE account_type_id in (1,2,3)
                    ORDER BY s.full_name;"""

    sitestats = """SELECT s.id,
                       s.display,
                       TOTAL(m.stop_datetime IS NOT NULL) as "Tutoring Sessions",
                       ROUND( (TOTAL(JULIANDAY(m.stop_datetime) - JULIANDAY(m.start_datetime)) * 24), 2)  as "Total Hours"
                    FROM tutor_site s
                    LEFT JOIN tutor_profile t on t.site_id = s.id
                    LEFT JOIN tutor_meetingmembership tm on t.user_id = tm.user_id
                    LEFT JOIN tutor_meeting m on tm.meeting_id = m.id
                    WHERE JULIANDAY('now') - JULIANDAY(m.stop_datetime) < 7
                    GROUP BY s.id;"""

    unfulfilledrequests = """SELECT r.id as "Request Id",
                               ts.display as "Subject",
                               tp.full_name as "Requested For",
                               tp.user_id as "User ID",
                               r.notes,
                               r.timestamp
                            FROM tutor_tutorrequest r
                            LEFT JOIN tutor_profile tp on r.user_id = tp.user_id
                            LEFT JOIN tutor_subject ts on r.subject_id = ts.id
                            WHERE active = 1
                              AND meeting_id IS NULL;"""

    fulfilledrequests = """SELECT s.id as "User ID",
                               s.full_name as "Full Name",
                               tm.meeting_id as "Meeting ID",
                               m.scheduled_start as "Scheduled Start",
                               m.stop_datetime as "Meeting End",
                               tm.cancel_timestamp as "Cancel Timestamp",
                               CASE WHEN ( m.stop_datetime IS NOT NULL )
                                    THEN 'Successful'
                                    ELSE 'Cancelled: ' || tm.cancel_reason
                               END as "Completed Meeting Status"
                            FROM tutor_profile s
                            LEFT JOIN tutor_tutorrequest r on s.user_id = r.user_id
                            CROSS JOIN tutor_meetingmembership tm on s.user_id = tm.user_id
                            LEFT JOIN tutor_meeting m on tm.meeting_id = m.id
                            WHERE r.meeting_id IS NOT NULL
                            GROUP BY s.id, m.id, m.scheduled_start, tm.cancel_timestamp
                            ORDER BY s.id, "Completed Meeting Status";"""

    duplicateemails = """SELECT user_id,
                               tp.full_name,
                               au.email,
                               tp.phone_number,
                               last_login
                            FROM auth_user au
                            JOIN tutor_profile tp on au.id = tp.user_id
                            JOIN (SELECT id, email FROM auth_user GROUP BY email HAVING COUNT(*) > 1) as b
                            ON au.email = b.email
                            ORDER BY au.email, au.last_login desc;"""

    prospecttracker = """select au.id as "Tutor ID",
                              date_joined as "Registration Date",
                              full_name as "Full Name",
                              email as "Email",
                              phone_number as "Phone",
                              tutee_contact as "Contact Info",
                              te.display as "Ethnicity",
                              tg.display as "Gender",
                              tp.display as "Pronouns",
                              JULIANDAY(max(o3.completed, o4.completed, o9.completed, o11.completed)) -
                              JULIANDAY(date_joined) as "Days Between Registration and Self-Paced Training Completed",
                              max(o3.completed, o4.completed, o9.completed, o11.completed) as "Self-Paced Training Completed",
                              tl.completed as "Live Training Completed",
                              CASE WHEN (o3.completed IS NOT NULL AND
                                         o4.completed IS NOT NULL AND
                                         o9.completed IS NOT NULL AND
                                         o11.completed AND
                                         tl.completed AND
                                         tb.status is 'Approved' )
                                                   THEN 'Y'
                                                   ELSE 'N'
                                               END as "Ready to Start"
                        
                        from tutor_profile
                        join auth_user au on tutor_profile.user_id = au.id
                        join tutor_ethnicity te on tutor_profile.ethnicity_id = te.id
                        join tutor_gender tg on tutor_profile.gender_id = tg.id
                        join tutor_pronouns tp on tutor_profile.pronouns_id = tp.id
                        join tutor_livesession tl on au.id = tl.user_id
                        join tutor_orientation3 o3 on au.id = o3.user_id
                        join tutor_orientation4 o4 on au.id = o4.user_id
                        join tutor_orientation9 o9 on au.id = o9.user_id
                        join tutor_orientation11 o11 on au.id = o11.user_id
                        join tutor_backgroundcheckrequest tb on au.id = tb.user_id

                        where account_type_id is 4;"""

    activetutors = """SELECT tp.user_id as "Tutor ID",
                          tp.full_name as "Full Name",
                          au.email as "Email",
                          tp.phone_number as "Phone",
                          tp.offered_hours as "Offered Hours",
                          tp.tutee_contact as "Contact Info",
                          COUNT(distinct tm.id) as "Times Connected",
                          COUNT( DISTINCT (case when tmm.cancel_timestamp IS NOT NULL
                                   THEN tm.id end)) as "Times They Canceled",
                          ROUND( (TOTAL( DISTINCT CASE WHEN tm.stop_datetime IS NOT NULL THEN JULIANDAY(tm.stop_datetime) - JULIANDAY(tm.start_datetime) end) * 24), 2)  as "Total Hours Logged All Time",
                          ROUND( (TOTAL( DISTINCT CASE WHEN tm.stop_datetime IS NOT NULL AND JULIANDAY('now') - JULIANDAY(tm.stop_datetime) < 120
                                   THEN JULIANDAY(tm.stop_datetime) - JULIANDAY(tm.start_datetime) end) * 24), 2)  as "Total Hours This Semester",
                          ROUND( tp.offered_hours * ((JULIANDAY('now') - JULIANDAY(au.date_joined))/7), 2) as "Total Offered Hours All Time",
                          IFNULL(ROUND(
                              (TOTAL( DISTINCT CASE WHEN tm.stop_datetime IS NOT NULL THEN JULIANDAY(tm.stop_datetime) - JULIANDAY(tm.start_datetime) end) * 24)/
                              (tp.offered_hours * ((JULIANDAY('now') - JULIANDAY(au.date_joined))/7)), 2), 0) as "Percent Hours Fulfilled All Time",
                          IFNULL(ROUND(
                              (TOTAL( DISTINCT CASE WHEN tm.stop_datetime IS NOT NULL AND JULIANDAY('now') - JULIANDAY(tm.stop_datetime) < 120
                                   THEN JULIANDAY(tm.stop_datetime) - JULIANDAY(tm.start_datetime) end) * 24) /
                              (tp.offered_hours * ((JULIANDAY('now') - JULIANDAY('now', '-120 days'))/7)), 2),0) as "Percent Hours Fulfilled This Semester"
                       FROM tutor_profile tp
                       LEFT JOIN tutor_backgroundcheckrequest bc on bc.user_id = tp.user_id
                       LEFT JOIN tutor_livesession tl on tp.user_id = tl.trainer_id
                       LEFT JOIN tutor_orientation3 o3 on tp.user_id = o3.user_id
                       LEFT JOIN tutor_orientation4 o4 on tp.user_id = o4.user_id
                       LEFT JOIN tutor_orientation9 o9 on tp.user_id = o9.user_id
                       LEFT JOIN tutor_orientation11 o11 on tp.user_id = o11.user_id
                       LEFT JOIN tutor_meetingmembership tmm on tp.user_id = tmm.user_id
                       LEFT JOIN tutor_meeting tm on tmm.meeting_id = tm.id
                       LEFT JOIN tutor_meeting_attendance tma on tp.user_id
                       LEFT JOIN auth_user au on tp.user_id = au.id
                       WHERE tp.account_type_id = 4
                       GROUP BY tp.user_id;"""

    studentinfo = """select tp.user_id as "Student ID",
                          au.date_joined as "Registration Date",
                          full_name as "Full Name",
                          nickname as "Nickname",
                          email as "Email",
                          phone_number as "Phone",
                          ts.display as "Partner Organization Site",
                          COUNT(tt.user_id) as "Requests Made",
                          COUNT(tm.id) as "Connections"
                    
                    from auth_user au
                    left join tutor_profile tp on tp.user_id = au.id
                    left join tutor_tutorrequest tt on tp.user_id = tt.user_id
                    left join tutor_site ts on tp.site_id = ts.id
                    left join tutor_meeting tm on tt.meeting_id = tm.id
                    where account_type_id in (1,2,3)
                    group by au.id;"""

    partnerorganizations = """select display,
                                  COUNT(tp.user_id) as "Created Student Profiles",
                                  COUNT(distinct tma.user_id) as "Students Tutored"
                            
                            from tutor_site
                            join tutor_profile tp on tutor_site.id = tp.site_id
                            join tutor_meeting_attendance tma on tp.user_id = tma.user_id
                            group by site_id;"""

    weeklysessions = """with tutors as (select *
                           from tutor_profile
                           left join auth_user au on tutor_profile.user_id = au.id where account_type_id is 4),
            
            students as (select *
                       from tutor_profile
                       left join auth_user au on tutor_profile.user_id = au.id where account_type_id in (1,2,3))
            select meeting.id as "Meeting #",
                  max(tutors.full_name) as "Tutor Name",
                  max(tutors.user_id) as "Tutor ID",
                  max(tutors.email) as "Tutor Email",
                  max(tutors.phone_number) as "Tutor Phone",
                  max(students.full_name) as "Student Name",
                  max(students.user_id) as "Student ID",
                  max(students.email) as "Student Email",
                  max(students.phone_number) as "Student Phone",
                  site.display as "Partner Site",
                  loc.display as "Site Location",
                  subj.display as "Subject",
                  meeting.created_at as "Connection Date",
                  meeting.scheduled_start as "Scheduled Time",
                  meeting.start_datetime as "Clock In",
                  meeting.stop_datetime as "Clock Out",
                  meeting.notes as "Tutor Notes",
                  Case when meeting.follow_up_meeting_id is not null then 'Y' else 'N' end as "Repeat Session"
            
            
            from tutor_meetingmembership membership
            left outer join tutor_meeting meeting on membership.meeting_id = meeting.id
            left outer join tutor_subject subj on meeting.subject_id = subj.id
            left outer join tutors on membership.user_id = tutors.user_id
            left outer join students on membership.user_id = students.user_id
            left outer join tutor_site site on students.site_id = site.display
            left outer join tutor_sitelocation loc on site.id = loc.site_id
            left outer join tutor_meeting_attendance s_attend on meeting.id = s_attend.meeting_id
            group by meeting.id, null;"""

    tutoringissues = """select submitter_id as "User ID",
                          tp.full_name as "Full Name",
                          au.email as "Email",
                          tp.phone_number as "Phone",
                          ti.id as "Ticket #",
                          ti.timestamp as "Submission Date",
                          ti.description as "Description",
                          ti.status as "Status"
                    
                    from tutor_issue ti
                    left join auth_user au on ti.submitter_id = au.id
                    left join tutor_profile tp on au.id = tp.user_id
                    order by ti.timestamp desc;"""
    
    # Helper class for organization
    class SQLTable:
        title = ""
        sqlstring = ""

        def __init__(self, title, sqlstring):
            self.title = title
            self.sqlstring = sqlstring

    # List of all tables to export and their SQL statements.
    sqllist = [SQLTable("profiles", "SELECT * FROM TUTOR_PROFILE"),
               SQLTable("meetings", "SELECT * FROM TUTOR_MEETING"),
               SQLTable("requests", "SELECT * FROM TUTOR_TUTORREQUEST"),
               SQLTable("sites", "SELECT * FROM TUTOR_SITE"),
               SQLTable("total_profiles", totals),
               SQLTable("tutor_info", tutorinfo),
               SQLTable("student_info", studentinfo),
               SQLTable("site_stats", sitestats),
               SQLTable("unfulfilled_requests", unfulfilledrequests),
               SQLTable("fulfilled_requests", fulfilledrequests),
               SQLTable("duplicate_emails", duplicateemails),
               SQLTable("prospect_tracker", prospecttracker),
               SQLTable("active_tutors", activetutors),
               SQLTable("student_info", studentinfo),
               SQLTable("partner_organizations", partnerorganizations),
               SQLTable("weekly_sessions", weeklysessions),
               SQLTable("tutoring_issues", tutoringissues), ]

    # Begin backup
    log = "Backup started at "
    start_time = datetime.now()
    log += str(start_time) + "...\n"

    # Create new folder for today and move into it
    folder = date.today().strftime("%Y-%m-%d")
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    BACKUP_DIR = os.path.join(ROOT_DIR, 'backups')
    FOLDER_DIR = os.path.join(BACKUP_DIR, folder)
    try:
        os.mkdir(FOLDER_DIR)

    except FileNotFoundError:  # Backup folder doesn't exist: Make a new one
        os.mkdir(BACKUP_DIR)
        os.mkdir(FOLDER_DIR)

    except FileExistsError:  # A folder for today already exists, overwrite it
        pass

    try:
        # Connect to database
        log += "Connecting to database... "
        SQL_PATH = os.path.join(ROOT_DIR, "db.sqlite3")
        conn = sqlite3.connect(SQL_PATH, isolation_level=None,
                               detect_types=sqlite3.PARSE_COLNAMES)
        log += "Successful\n"

        # Backup the database
        log += "Backing up database... "
        shutil.copy(SQL_PATH, FOLDER_DIR)
        log += "Successful\n"

        # Export each table into CSV file
        log += "Exporting tables...\n"
        for table in sqllist:
            log += table.title + "... "
            db_df = read_sql_query(table.sqlstring, conn)
            FILE_NAME = os.path.join(FOLDER_DIR, table.title + '.csv')
            db_df.to_csv(FILE_NAME, index=False)
            log += "Exported\n"
        log += "Data backed up successfully into {}\n".format(FOLDER_DIR)

        # Close the connection
        conn.close()
        log += "Finished successfully at "

    except Exception as e:
        log += str(e) + "\n"
        log += "Finished unsuccessfully at "

    finally:
        end_time = datetime.now()
        elapsed = end_time - start_time

        # Write to log file
        log += str(end_time) + ".\nTime elapsed: " + str(elapsed)
        with open(os.path.join(FOLDER_DIR, 'log.txt'), "w") as logfile:
            logfile.write(log)
        shutil.make_archive(FOLDER_DIR, 'zip', FOLDER_DIR)
        shutil.rmtree(FOLDER_DIR)
