from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from datetime import timedelta
from dominoapp.models import Player, SummaryPlayer

class Command(BaseCommand):
    help = 'Agrupa datos de SummaryPlayer por mes/semana y limpia registros antiguos.'

    def handle(self, *args, **options):
        now = timezone.now()
        start_of_current_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 1. Obtener todos los jugadores que tienen datos
        player_ids = SummaryPlayer.objects.values_list('player_id', flat=True).distinct()
        player_ids = Player.objects.filter(id__in=player_ids).values_list('id', flat=True).distinct()
        
        for player_id in player_ids:
            with transaction.atomic():
                # --- FASE 1: AGRUPAR MESES ANTERIORES AL MES ACTUAL ---
                # Buscamos registros de meses pasados que no estén ya en el día 1 del mes
                first_day_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                old_records = SummaryPlayer.objects.filter(
                    player_id=player_id,
                    created_at__lt=first_day_current_month
                )

                if old_records.exists():
                    self.aggregate_by_period(player_id, old_records, period='month')

                # --- FASE 2: AGRUPAR SEMANAS DEL MES ACTUAL (EXCEPTO LA ACTUAL) ---
                # Buscamos registros entre el inicio del mes y el inicio de esta semana
                month_records_exists = SummaryPlayer.objects.filter(
                        player_id=player_id,
                        created_at__gte=first_day_current_month
                    ).exists()
                if month_records_exists:
                    for week in range(1, 5): # Asumiendo máximo 4 semanas por mes
                        start_of_week = first_day_current_month + timedelta(days=(week-1)*7)
                        end_of_week = start_of_week + timedelta(days=7)
                        
                        if end_of_week > start_of_current_week:
                            break

                        mid_records = SummaryPlayer.objects.filter(
                            player_id=player_id,
                            created_at__gte=start_of_week,
                            created_at__lt=end_of_week
                        )

                        if mid_records.exists():
                            self.aggregate_by_period(player_id, mid_records, period='week')
                
        self.stdout.write(self.style.SUCCESS('Limpieza y agregación completada con éxito.'))

    def aggregate_by_period(self, player_id, queryset, period):
        """
        Suma los valores y crea un único registro para el inicio del periodo.
        """
        # Identificamos los campos numéricos a sumar dinámicamente
        fields_to_sum = SummaryPlayer.get_available_fields()
        aggregation_query = {field: Sum(field) for field in fields_to_sum}
        
        # Agrupar por el inicio del periodo (esto es simplificado, 
        # en producción podrías iterar por cada mes/semana específico si hay varios)
        totals = queryset.aggregate(**aggregation_query)
        
        if totals[fields_to_sum[0]] is None: # Si no hay datos reales
            return

        # Determinar fecha de referencia (1er día del mes o 1er día de la semana)
        sample_date = queryset.first().created_at
        if period == 'month':
            ref_date = sample_date.replace(day=1, hour=0, minute=0, second=0)
        else: # week
            ref_date = (sample_date - timedelta(days=sample_date.weekday())).replace(hour=0, minute=0, second=0)

        # Crear o actualizar el registro consolidado
        SummaryPlayer.objects.update_or_create(
            player_id=player_id,
            created_at=ref_date,
            defaults={field: totals[field] for field in fields_to_sum}
        )

        # Borrar todos los registros del periodo que NO sean el consolidado recién creado
        queryset.exclude(created_at=ref_date).delete()