import subprocess
import os
import pydot
import sys
from html.parser import HTMLParser
import csv

class Layer():
    def __init__(self, ir_name, gna_name):
        self.ir_name = ir_name
        self.gna_name = gna_name

class IdentityLayer(Layer):
    def __init__(self, ir_name, gna_name, oscale):
        Layer.__init__(self, ir_name, gna_name)
        self.oscale = oscale
    '''
    def print_layer(self):
        print("Layer name is " + self.ir_name  + " " + self.gna_name  + " " + self.oscale)
    '''

class LabelHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.data_list = []
        self.list = []
        self.identity_wscale_map = {}
        self.identity_layer_map = {}

    def get_identity_layer_map(self):
        return self.identity_layer_map
    
    def get_identity_wscale_map(self):
        return self.identity_wscale_map

    def handle_data(self, data):
        self.data_list.append(data)

    def add_data_list(self):
        self.list.append(self.data_list)
        self.data_list = []

    def create_layer(self):
        for item in self.list:
            if("identity" in item[5]):
                curr_layer = IdentityLayer(item[5], item[2], item[29])
                layer_no = item[2].split("_")
                self.identity_layer_map[int(layer_no[1])] = curr_layer
                self.identity_wscale_map[int(layer_no[1])] = item[29]

def parse_dot():
    f = open("/home/adattatr/script/blob/gna-blob-head.dot", "r")
    data = f.read()
    P_list = pydot.graph_from_dot_data(data)
    label_parser = LabelHTMLParser()
    for item in P_list[0].obj_dict['nodes'].keys():
        label_parser.feed(P_list[0].obj_dict['nodes'][item][0]['attributes']['label'])
        label_parser.add_data_list()
    
    label_parser.create_layer()
    return label_parser

def main():
    '''
    for frame in range(0,1):
        os.mkdir(str(frame))
        os.mkdir(str(frame) + "/identity")
        subprocess.run(["scp", "root@172.25.115.5:/opt/google/containers/android/rootfs/android-data/data/local/tmp/layers/" + str(frame) + "/*-kActIdentity_output.txt", "./" + str(frame) + "/identity/"])
    '''
    graph = parse_dot()

    for frame in range(0,1):
        layers_op = []
        file_count = 0
        for filename in os.listdir(os.getcwd() + "/" + str(frame) + "/identity/"):
            layers_op.append([])
            layers_op[file_count].append(filename)
            #    '''
            with open(os.getcwd() + "/" + str(frame) + "/identity/" + str(filename), 'r') as f:
                layer_op = []
                output_list = []

                for data in f:
                    order = data.replace("\n", ",").replace('\n','').strip()
                    output = order.split(",")
                    output_list.append(output[0])
                    #output_list 
            layers_op[file_count].append(len(output_list))
            layers_op[file_count].append(output_list)
            file_count += 1
        
        under_flow_count = 0
        for item in layers_op:
            over_flow_count = 0
            under_flow_count = 0
            over_flow_count += item[2].count("-64")
            over_flow_count += item[2].count("64")
            under_flow_count += item[2].count("0")
            item.append(over_flow_count)
            item.append(under_flow_count)

        with open("layers.csv", 'w', newline="\n") as csvfile:
            layerwriter = csv.writer(csvfile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
            layerwriter.writerow(["Layer Number", "Overflow Count", "Underflow Count", "Scale Factor"])
            for item in layers_op:
                output = item[0].split("_")
                print("Layer_number = " + output[0] + " " + str(item[3]) + " Scale Factor = " + str(graph.get_identity_wscale_map()[int(output[0])]))
                layerwriter.writerow([output[0] , str(item[3]), str(item[4]), str(graph.get_identity_wscale_map()[int(output[0])])])
        #print(graph.get_identity_map().items())  

        # List of one or more "pydot.Dot" instances deserialized from this file.
        

    

if __name__ == "__main__":
    main()
