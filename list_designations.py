from django.db import connections
for alias in connections:
    try:
        with connections[alias].cursor() as c:
            c.execute("select name, full_name from globals_designation order by name")
            print(alias, "->", c.fetchall())
    except Exception as e:
        print(alias, "-> no:", str(e)[:100])
