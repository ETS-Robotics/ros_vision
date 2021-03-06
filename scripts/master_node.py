#!/usr/bin/env python
import roslib; roslib.load_manifest('ros_vision')

import rospy
import rospkg
import os
import yaml
import collections
from RosVision.message_factory import MessageFactory
from RosVision.Filters.filter import Filter
import ros_vision.srv
import ros_vision.msg
from Master.Workspace.workspace import Workspace
from Master.Scheduler.scheduler import Scheduler


rospy.init_node('vision_master')

def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())

def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

def get_workspace(req):
    res = ros_vision.srv.GetWorkspaceResponse()
    res.workspace = MessageFactory.create_workspace_message_from_workspace(workspace)

    return res

def load_workspace(req):
    res = ros_vision.srv.LoadWorkspaceResponse()
    rospack = rospkg.RosPack()
    name = os.path.join(rospack.get_path("ros_vision"), "workspaces/" + req.name + ".yaml")

    if not os.path.exists(name):
        name = req.name + ".yaml"

    workspace.reset()
    workspace.name = req.name

    with open(name, 'r') as f:
        for filtergroup_name, filters in yaml.load(f).items():
            workspace.add_group(filtergroup_name, None, filters)

    while not workspace.is_ready() and not rospy.is_shutdown():
        rospy.sleep(0.1)

    res.workspace = MessageFactory.create_workspace_message_from_workspace(workspace)

    return res

def save_workspace(req):
    rospack = rospkg.RosPack()
    serialized_workspace = collections.OrderedDict()
    types = {'str': str, 'int': int, 'float': float, 'bool': bool}

    with open(os.path.join(rospack.get_path("ros_vision"), "workspaces/" + req.name + ".yaml"), 'w') as f:
        for group_name, group in workspace.groups.items():
            filters = collections.OrderedDict()

            for filter in group.filters.values():
                parameters = collections.OrderedDict()
                parameters["type"] = filter.type

                for input in filter.inputs:
                    parameters[input.name] = input.topic

                for parameter in filter.parameters:
                    get_parameter_request = ros_vision.srv.GetParameterValueRequest()
                    get_parameter_request.filter_name = filter.name
                    get_parameter_request.parameter_name = parameter.name

                    rospy.wait_for_service("%s/get_parameter" % group_name)
                    get_parameter = rospy.ServiceProxy("%s/get_parameter" % group_name, ros_vision.srv.GetParameterValue)
                    parameter_value = get_parameter(get_parameter_request).parameter_value

                    if parameter_value != parameter.default:
                        parameters[parameter.name] = types[parameter.type](parameter_value)

                filters[filter.name] = parameters

            serialized_workspace[group_name[1:]] = filters

        f.write(yaml.dump(serialized_workspace, default_flow_style=False))

    return ros_vision.srv.SaveWorkspaceResponse()

def list_workspaces(req):
    res = ros_vision.srv.ListWorkspacesResponse()
    rospack = rospkg.RosPack()
    res.workspaces = []

    for workspace in os.listdir(os.path.join(rospack.get_path("ros_vision"), "workspaces")):
        if workspace.endswith(".yaml"):
            res.workspaces.append(workspace[:-5])

    return res

def save_filterchain():
    pass

def create_filtergroup(req):
    workspace.add_group(req.name, req.order)

    return ros_vision.srv.CreateFilterGroupResponse()

def delete_filtergroup(req):
    delete_filter_srv_name = '/%s/delete_filter' % req.name
    rospy.wait_for_service(delete_filter_srv_name)
    workspace.groups["/" + req.name].kill()
    del workspace.groups["/" + req.name]
    workspace.update_workspace()

    return ros_vision.srv.DeleteFilterGroupResponse()

def list_filter_types(req):
    res = ros_vision.srv.ListFilterTypesResponse()
    descriptors = Filter.list_descriptors()

    for filter_name in descriptors.keys():
        res.filter_list.filters.append(MessageFactory.create_filter_message_from_descriptor(descriptors[filter_name]))

    return res

workspace = Workspace()
#scheduler = Scheduler(workspace)

get_workspace_service = rospy.Service('~get_workspace', ros_vision.srv.GetWorkspace, get_workspace)
list_workspaces_service = rospy.Service('~list_workspaces', ros_vision.srv.ListWorkspaces, list_workspaces)
load_workspace_service = rospy.Service('~load_workspace', ros_vision.srv.LoadWorkspace, load_workspace)
save_workspace_service = rospy.Service('~save_workspace', ros_vision.srv.SaveWorkspace, save_workspace)
create_filtergroup_service = rospy.Service('~create_filtergroup', ros_vision.srv.CreateFilterGroup, create_filtergroup)
delete_filtergroup_service = rospy.Service('~delete_filtergroup', ros_vision.srv.DeleteFilterGroup, delete_filtergroup)
list_filter_types_service = rospy.Service('~list_filter_types', ros_vision.srv.ListFilterTypes, list_filter_types)

yaml.add_representer(collections.OrderedDict, dict_representer)
yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, dict_constructor)

workspace_name = rospy.get_param("~workspace", None)
if workspace_name:
    load_workspace(ros_vision.srv.LoadWorkspaceRequest(name=workspace_name))

#scheduler.run()
while not rospy.is_shutdown():
    rospy.sleep(1)
