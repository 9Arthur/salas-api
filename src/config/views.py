from django.db import connection
from django.http import JsonResponse


def healthz(request):
    # Sem try/except: banco fora derruba a consulta e o endpoint responde 500.
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok"}, status=200)
