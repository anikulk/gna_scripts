import subprocess
import os
import pydot
import sys
from html.parser import HTMLParser
import csv
import numpy as np
import gna_layers

class LabelHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.data_list = []
        self.list = []
        self.identity_wscale_map = {}
        self.affine_layer_map = {}
        self.identity_layer_map = {}

    def get_identity_layer_map(self):
        return self.identity_layer_map

    def get_affine_layer_map(self):
        return self.affine_layer_map

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
                curr_layer = gna_layers.IdentityLayer(item[5], item[2], item[29])
                print("item2 = " + str(item[2]))
                layer_no = item[2].split("_")
                print("identity layer" + str(curr_layer))
                self.identity_layer_map[int(layer_no[1])] = curr_layer
                print("identity layer number" + str(layer_no[1]))
                self.identity_wscale_map[int(layer_no[1])] = item[29]
                print("identity layer wscale" + str(item[29]))
            if("kDnnAffineOp" in item[2]):
                curr_layer = gna_layers.AffineLayer(item[5], item[2], item[44], item[11])
                layer_no = item[2].split("_")
                self.affine_layer_map[int(layer_no[1])] = curr_layer
            if("kDnnDiagonalOp" in item[2]):
                curr_layer = gna_layers.AffineLayer(item[5], item[2], item[44], item[11])
                layer_no = item[2].split("_")
                self.affine_layer_map[int(layer_no[1])] = curr_layer


def convert_and_write_to_csv(frame_start, frame_end, filelist, csvname):
    with open(csvname, 'w', newline="\n") as csvfile:
        layerwriter = csv.writer(csvfile, delimiter=',',
                         quoting=csv.QUOTE_MINIMAL)
        for file in filelist:
            for frame in range(frame_start, frame_end):
                with open(os.getcwd() + "/" + str(frame) + "/identityfp32/" + str(file) + "_kDnnPiecewiselinearOp-2048-2048-kActIdentity_output.txt", 'r') as f:
                    output_list = []
                    for data in f:
                        #order = data.replace("\n", ",").replace('\n','').strip()
                        output = data.split("\n") # Can just split by \n?
                        output_list.append(float(output[0].strip()))
                    layerwriter.writerow(output_list)

def parse_dot(dot_file_path):
    f = open(str(dot_file_path), "r")
    data = f.read()
    P_list = pydot.graph_from_dot_data(data)
    label_parser = LabelHTMLParser()
    for item in P_list[0].obj_dict['nodes'].keys():
        label_parser.feed(P_list[0].obj_dict['nodes'][item][0]['attributes']['label'])
        label_parser.add_data_list()

    label_parser.create_layer()
    return label_parser

def main():
    if (len(sys.argv) != 7) :
        print("Usage : python3 check_op.py no_of_frames dut_ip_address copy_layer_files=true/false parse_graph=true/false result_filename path_to_dot_file")
        exit()

    num_frame = int(sys.argv[1])
    dut_ip = sys.argv[2]
    copy_files = sys.argv[3]
    parse_graph = sys.argv[4]
    result_filename = sys.argv[5]
    dot_file_path = sys.argv[6]
    print(dut_ip)

    if copy_files == 'true':
        for frame in range(0, num_frame):
            os.mkdir(str(frame))
            os.mkdir(str(frame) + "/identity")
            os.mkdir(str(frame) + "/identityfp32")
            subprocess.run(["scp", "root@" + dut_ip + ":/usr/local/ml_benchmark/layers/" + str(frame) + "/*-kActIdentity_output.txt", "./" + str(frame) + "/identity/"])
            subprocess.run(["scp", "root@" + dut_ip + ":/usr/local/ml_benchmark/ref_layers/" + str(frame) + "/*-kActIdentity_output.txt", "./" + str(frame) + "/identityfp32"])
    #convert_and_write_to_csv(0, 3, [42, 66, 54, 30, 122, 143, 186, 164, 217, 238, 259, 281, 312, 333, 354, 376, 407, 428, 449, 470, 502, 523, 544, 566], "ln_ip.csv")
    if parse_graph == 'true':
        graph = parse_dot(dot_file_path)
        print(graph.get_affine_layer_map()[144].get_oscale())
        print(graph.get_affine_layer_map()[144].get_wscale())

        with open(result_filename, 'w', newline="\n") as csvfile:
            layerwriter = csv.writer(csvfile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
            layerwriter.writerow(["Frame Number ","Layer Number", "Overflow Count", "Underflow Count", "Max GNA value", "Scale Factor", "Max FP32 value", "Mean of Overflowing FP32 values", "Median", "GNA Layer Name", "IR Layer Name"])

        for frame in range(0, num_frame):
            layers_op = []
            fp32_layers_op = []
            file_count = 0
            for filename in os.listdir(os.getcwd() + "/" + str(frame) + "/identityfp32/"):
                layers_op.append([])
                fp32_layers_op.append([])
                fp32_layers_op[file_count].append(filename)
                layers_op[file_count].append(filename)

                with open(os.getcwd() + "/" + str(frame) + "/identity/" + str(filename), 'r') as f:
                    layer_op = []
                    output_list = []

                    for data in f:
                        order = data.replace("\n", ",").replace('\n','').strip()
                        output = order.split(",") # Can just split by \n?
                        output_list.append(output[0])

                with open(os.getcwd() + "/" + str(frame) + "/identityfp32/" + str(filename), 'r') as f:
                    fp32_layer_op = []
                    fp32_output_list = []

                    for data in f:
                        order = data.replace("\n", ",").replace('\n','').strip()
                        output = order.split(",") # Can just split by \n?
                        fp32_output_list.append(output[0])

                layers_op[file_count].append(len(output_list))
                layers_op[file_count].append(output_list)
                fp32_layers_op[file_count].append(len(fp32_output_list))
                fp32_layers_op[file_count].append(fp32_output_list)
                file_count += 1

            for i in range(0, len(layers_op)):
                mean = 0
                median = 0
                item = layers_op[i]
                fp_item = fp32_layers_op[i]
                over_flow_count = 0
                under_flow_count = 0
                over_flow_count += item[2].count("-128")
                over_flow_count += item[2].count("-127.996")
                over_flow_count += item[2].count("127.996") # Why is it 63.998
                gna_values = np.array(item[2])

                searchval = "-64"
                ii = np.where(gna_values == searchval)[0]
                ii2 = np.where(gna_values == "128")[0]
                fp32_overflow_vals = []

                for index in ii:
                    fp32_overflow_vals.append(float(fp_item[2][index]))
                for index in ii2:
                    fp32_overflow_vals.append(float(fp_item[2][index]))
                if(len(fp32_overflow_vals) != 0):
                    fp32_OF = np.array(fp32_overflow_vals)
                    fp32_OF_abs = np.abs(fp32_OF)
                    median = np.median(fp32_OF_abs)
                    mean = np.mean(fp32_OF_abs)
                gna_max = max(abs(float(value)) for value in item[2])
                fp32_max = max(abs(float(value)) for value in fp_item[2])
                under_flow_count += item[2].count("0")
                item.append(over_flow_count)
                item.append(under_flow_count)
                item.append(str(gna_max))
                item.append(str(fp32_max))
                item.append(str(mean))
                item.append(str(median))


            for item in layers_op:
                print("item in layers_op " + str(item))
                print("item[0] = " + str(item[0]))
                output = item[0].split("_")
                with open(result_filename, 'a', newline="\n") as csvfile:
                    layerwriter = csv.writer(csvfile, delimiter=',',
                        quotechar='|', quoting=csv.QUOTE_MINIMAL)
                    print(frame)
                    print(output[0])
                    print(str(item[3]))
                    print(str(item[4]))
                    #str(item[5]),
                    #print(str(graph.get_identity_wscale_map()[int(output[0])]))
                    #, str(item[6]), str(item[7]), str(item[8]),
                    #print(graph.get_identity_layer_map()[int(output[0])].get_gna_name())
                    #, graph.get_identity_layer_map()[int(output[0])].get_ir_name(), graph.get_affine_layer_map()[int(output[0]) - 1].get_ir_name(), graph.get_affine_layer_map()[int(output[0]) - 1].get_wscale(), graph.get_affine_layer_map()[int(output[0]) - 1].get_oscale()])
                    if (int(output[0]) != 43):
                        if ((int(output[0]) != 205)):
                            if( (int(output[0]) not in graph.get_identity_layer_map()) and (int(output[0]) not in graph.get_affine_layer_map())):
                                print(output[0])
                            else :
                                layerwriter.writerow([frame, output[0] , str(item[3]), str(item[4]), str(item[5]), str(graph.get_identity_wscale_map()[int(output[0])]), str(item[6]), str(item[7]), str(item[8]), graph.get_identity_layer_map()[int(output[0])].get_gna_name(), graph.get_identity_layer_map()[int(output[0])].get_ir_name(), graph.get_affine_layer_map()[int(output[0]) - 1].get_ir_name(), graph.get_affine_layer_map()[int(output[0]) - 1].get_wscale(), graph.get_affine_layer_map()[int(output[0]) - 1].get_oscale()])

            #print(graph.get_identity_map().items())

        # List of one or more "pydot.Dot" instances deserialized from this file.

if __name__ == "__main__":
    main()
