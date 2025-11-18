import logging
from rest_framework import status
from rest_framework.response import Response
from datetime import datetime
from dominoapp.serializers import TournamentCreateSerializer
logger = logging.getLogger('django')


class TournamentService:
    
    @staticmethod
    def process_create(request):
        
        today = datetime.now()
        start_date = datetime.strptime(request.data.get('start_at'), "%d-%m-%Y %H:%M:%S")
        deadline = datetime.strptime(request.data.get('deadline'), "%d-%m-%Y %H:%M:%S")
                
        if deadline <= today:
            return Response(data={
                "status": "error",
                "message": "Deadline must be a future date."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if start_date <= deadline:
            return Response(data={
                "status": "error",
                "message": "Start date must be after the deadline."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        request.data['start_at'] = start_date
        request.data['deadline'] = deadline
        
        serializer = TournamentCreateSerializer(data=request.data)
        try:
            if serializer.is_valid():
                serializer.save()
                return Response(data={
                    "status": "success",
                    "tournament": serializer.data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(data={
                    "status": "error",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.critical(f'Exception occurred while creating tournament: {str(e)}')
            return Response(data={
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_409_CONFLICT)