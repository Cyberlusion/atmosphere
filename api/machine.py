"""
Atmosphere service machine rest api.

"""
from django.contrib.auth.models import User
from django.core.paginator import Paginator,\
    PageNotAnInteger, EmptyPage

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from threepio import logger

from authentication.decorators import api_auth_token_required

from core.models.machine import filter_core_machine,\
    convertEshMachine, update_machine_metadata

from api import prepareDriver, failureJSON
from api.serializers import ProviderMachineSerializer,\
    PaginatedProviderMachineSerializer


def all_filtered_machines(request, provider_id, identity_id):
    """
    Return all filtered machines. Uses the most common,
    default filtering method.
    """
    esh_driver = prepareDriver(request, identity_id)
    esh_machine_list = esh_driver.list_machines()
    esh_machine_list = esh_driver.filter_machines(
        esh_machine_list,
        black_list=['eki-', 'eri-'])
    core_machine_list = [convertEshMachine(esh_driver, mach, provider_id)
                         for mach in esh_machine_list]
    filtered_machine_list = filter(filter_core_machine, core_machine_list)
    return filtered_machine_list


class MachineList(APIView):
    """
    Represents:
        A Manager of Machine
        Calls to the Machine Class
    TODO: POST when we have programmatic image creation/snapshots
    """

    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        """
        Using provider and identity, getlist of machines
        TODO: Cache this request
        """
        filtered_machine_list = all_filtered_machines(request, provider_id, identity_id)
        serialized_data = ProviderMachineSerializer(filtered_machine_list,
                                                    many=True).data
        response = Response(serialized_data)
        return response


class MachineHistory(APIView):
    """
    A MachineHistory provides machine history for an identity.

    GET - A chronologically ordered list of ProviderMachines for the identity.
    """

    @api_auth_token_required
    def get(self, request, provider_id, identity_id):
        data = request.DATA
        user = User.objects.filter(username=request.user)

        if user and len(user) > 0:
            user = user[0]
        else:
            errorObj = failureJSON([{
                'code': 401,
                'message': 'User not found'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)

        esh_driver = prepareDriver(request, identity_id)

        # Historic Instances
        all_machines_list = all_filtered_machines(request,
                                                  provider_id,
                                                  identity_id)

        # Reverse chronological order
        all_machines_list.reverse()

        if all_machines_list:
            history_machine_list =\
                [m for m in all_machines_list if
                 m.machine.created_by == user]
        else:
            history_machine_list = []

        page = request.QUERY_PARAMS.get('page')
        if page:
            paginator = Paginator(history_machine_list, 20)
            try:
                history_machine_page = paginator.page(page)
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                history_machine_page = paginator.page(1)
            except EmptyPage:
                # Page is out of range.
                # deliver last page of results.
                history_machine_page = paginator.page(paginator.num_pages)
            serialized_data = \
                PaginatedProviderMachineSerializer(
                    history_machine_page).data
        else:
            serialized_data = ProviderMachineSerializer(
                history_machine_list).data

        response = Response(serialized_data)
        response['Cache-Control'] = 'no-cache'
        return response


class Machine(APIView):
    """
    Represents:
        Calls to modify the single machine
    TODO: DELETE when we allow owners to 'end-date' their machine..
    """

    @api_auth_token_required
    def get(self, request, provider_id, identity_id, machine_id):
        """
        Lookup the machine information
        (Lookup using the given provider/identity)
        Update on server (If applicable)
        """
        esh_driver = prepareDriver(request, identity_id)
        eshMachine = esh_driver.get_machine(machine_id)
        coreMachine = convertEshMachine(esh_driver, eshMachine, provider_id)
        serialized_data = ProviderMachineSerializer(coreMachine).data
        response = Response(serialized_data)
        return response

    @api_auth_token_required
    def patch(self, request, provider_id, identity_id, machine_id):
        """
        TODO: Determine who is allowed to edit machines besides
            coreMachine.owner
        """
        user = request.user
        data = request.DATA
        esh_driver = prepareDriver(request, identity_id)
        esh_machine = esh_driver.get_machine(machine_id)
        coreMachine = convertEshMachine(esh_driver, esh_machine, provider_id)

        if not user.is_staff and user is not coreMachine.machine.created_by:
            logger.warn('%s is Non-staff/non-owner trying to update a machine'
                        % (user.username))
            errorObj = failureJSON([{
                'code': 401,
                'message':
                'Only Staff and the machine Owner '
                + 'are allowed to change machine info.'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)

        coreMachine.machine.update(request.DATA)
        serializer = ProviderMachineSerializer(coreMachine,
                                               data=data, partial=True)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            update_machine_metadata(esh_driver, esh_machine, data)
            serializer.save()
            logger.info(serializer.data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @api_auth_token_required
    def put(self, request, provider_id, identity_id, machine_id):
        """
        TODO: Determine who is allowed to edit machines besides
            coreMachine.owner
        """
        user = request.user
        data = request.DATA
        esh_driver = prepareDriver(request, identity_id)
        esh_machine = esh_driver.get_machine(machine_id)
        coreMachine = convertEshMachine(esh_driver, esh_machine, provider_id)

        if not user.is_staff and user is not coreMachine.machine.created_by:
            logger.warn('Non-staff/non-owner trying to update a machine')
            errorObj = failureJSON([{
                'code': 401,
                'message':
                'Only Staff and the machine Owner '
                + 'are allowed to change machine info.'}])
            return Response(errorObj, status=status.HTTP_401_UNAUTHORIZED)
        coreMachine.machine.update(data)
        serializer = ProviderMachineSerializer(coreMachine,
                                               data=data, partial=True)
        if serializer.is_valid():
            logger.info('metadata = %s' % data)
            update_machine_metadata(esh_driver, esh_machine, data)
            serializer.save()
            logger.info(serializer.data)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
