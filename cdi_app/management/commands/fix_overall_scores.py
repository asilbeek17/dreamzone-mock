"""
Management command to recalculate overall scores with correct IELTS rounding
"""
from django.core.management.base import BaseCommand
from cdi_app.models import Result


class Command(BaseCommand):
    help = 'Recalculate overall scores for all results using IELTS rounding rules'

    def handle(self, *args, **options):
        results = Result.objects.all()
        count = 0
        
        for result in results:
            old_overall = result.overall
            
            # Recalculate with IELTS rounding
            total = float(result.listening) + float(result.reading) + float(result.writing) + float(result.speaking)
            average = total / 4
            
            # IELTS rounding rules
            decimal_part = average - int(average)
            
            if decimal_part < 0.25:
                new_overall = int(average)
            elif decimal_part < 0.75:
                new_overall = int(average) + 0.5
            else:
                new_overall = int(average) + 1.0
            
            if old_overall != new_overall:
                result.overall = new_overall
                result.save()
                count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated result for {result.booking.user.full_name}: {old_overall} → {new_overall}'
                    )
                )
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No results needed updating'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} result(s)'))
