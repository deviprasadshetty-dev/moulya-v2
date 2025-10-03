from app import create_app
from database import db
import sqlalchemy as sa

app = create_app()
with app.app_context():
    insp = sa.inspect(db.engine)
    print(insp.get_table_names())  # look for 'monthly_student_attendance'
    print('monthly_student_attendance' in insp.get_table_names())