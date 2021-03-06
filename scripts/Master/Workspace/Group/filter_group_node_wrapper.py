from collections import OrderedDict
from node import Node
import rosparam
import rospy
from ros_vision.srv import CreateFilter


class FilterGroupNodeWrapper:
    def __init__(self, name, filters=OrderedDict()):
        self.name = name
        self.node = Node("ros_vision", "filter_chain_node.py", name)
        self.reset_params()
        self.node.run()
        create_filter_srv_name = '/%s/create_filter' % name
        rospy.wait_for_service(create_filter_srv_name)
        self.create_filter = rospy.ServiceProxy(create_filter_srv_name, CreateFilter)

        i = 0
        for filter_name in filters.keys():
            i += 1

            if 'type' in filters[filter_name].keys():
                filter_type = filters[filter_name]['type']
                del filters[filter_name]['type']

                for parameter_name in filters[filter_name].keys():
                    rosparam.set_param('/%s/%s/%s' % (name, filter_name, parameter_name), str(filters[filter_name][parameter_name]))

                self.create_filter(filter_name, filter_type, i)

    def reset_params(self):
        for p in rosparam.list_params(self.name):
            rosparam.delete_param(p)

    def kill(self):
        self.node.kill()