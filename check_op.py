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
                layer_no = item[2].split("_")
                self.identity_layer_map[int(layer_no[1])] = curr_layer
                self.identity_wscale_map[int(layer_no[1])] = item[29]
            if("iden_infg" in item[5]):
                curr_layer = gna_layers.IdentityLayer(item[5], item[2], item[29])
                layer_no = item[2].split("_")
                self.identity_layer_map[int(layer_no[1])] = curr_layer
                self.identity_wscale_map[int(layer_no[1])] = item[29]
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

def count_range_in_list(li, min, max):
    ctr = 0
    for x in li:
        if min <= x <= max:
            ctr += 1
    return ctr

def calc_OF_UF(curr_gna_layer_op, curr_fp32_layer_op, graph):
    curr_gna_layer_modified = []
    gna_values = np.array(curr_gna_layer_op[2])
    layer_number = curr_gna_layer_op[0].split("_")

    overflow_val = 32768 / float(graph.get_identity_wscale_map()[int(layer_number[0])])
    of_count = count_range_in_list(gna_values, -overflow_val + 0.1, -overflow_val)
    of_count += count_range_in_list(gna_values, overflow_val - 0.1, overflow_val)
    fp32_overflow_vals = [] #-overflow_val + 1, -overflow_val, overflow_val - 1, overflow_val]

    #ii = np.where((gna_values > overflow_val - 1 and gna_values < overflow_val + 0.1) or
    #                  (gna_values < -overflow_val + 1 and gna_values > -overflow_val + 0.1))[0]
    indexes = np.where(np.logical_and(gna_values >= (overflow_val - 1 ), gna_values <= (overflow_val + 0.1)))
    indexes2 = np.where(np.logical_and(gna_values <= (-overflow_val), gna_values >= (-overflow_val + 0.1)))
    for index in indexes[0]:
        fp32_overflow_vals.append(float(curr_fp32_layer_op[2][index]))
    for index in indexes2[0]:
        fp32_overflow_vals.append(float(curr_fp32_layer_op[2][index]))

    #if(len(fp32_overflow_vals) != 0):
    fp32_OF = np.array(fp32_overflow_vals)
    fp32_OF_abs = np.abs(fp32_OF)
    median = np.median(fp32_OF_abs)
    mean = np.mean(fp32_OF_abs)

    gna_max = max(abs(float(value)) for value in curr_gna_layer_op[2])
    fp32_max = max(abs(float(value)) for value in curr_fp32_layer_op[2])
    under_flow_count = curr_gna_layer_op[2].count("0")
    curr_gna_layer_modified.append(of_count)
    curr_gna_layer_modified.append(under_flow_count)
    curr_gna_layer_modified.append(str(gna_max))
    curr_gna_layer_modified.append(str(fp32_max))
    curr_gna_layer_modified.append(str(mean))
    curr_gna_layer_modified.append(str(median))

    return curr_gna_layer_modified



def main():
    if (len(sys.argv) != 7) :
        print("Usage : python3 check_op.py no_of_samples dut_ip_address copy_gna_layer_files=true/false parse_graph=true/false result_filename path_to_dot_file")
        exit()

    num_sample = int(sys.argv[1])
    dut_ip = sys.argv[2]
    copy_files = sys.argv[3]
    parse_graph = sys.argv[4]
    result_filename = sys.argv[5]
    dot_file_path = sys.argv[6]

    if copy_files == 'true':
        os.mkdir("gna")
        #os.mkdir("cpu")
        for sample in range(1, num_sample):
            os.mkdir("gna/" + "sample" + str(sample))
            #os.mkdir("cpu/" + "sample" + str(sample))
            for frame in [3, 23, 37] :
                os.mkdir("gna/" + "sample" + str(sample) + "/" + str(frame))
                #os.mkdir("cpu/" + "sample" + str(sample) + "/" + str(frame))
                #os.mkdir("gna/" + "sample" + str(sample) / str(frame) + "/identity")
                #os.mkdir("sample" + str(sample) / str(frame) + "/identityfp32")
                subprocess.run(["scp", "root@" + dut_ip + ":/usr/local/ml_benchmark/gna/sample" + str(sample) + "/" + str(frame) + "/*-kActIdentity_output.txt", "./gna/sample" + str(sample) + "/" + str(frame)])
                #subprocess.run(["scp", "root@" + dut_ip + ":/usr/local/ml_benchmark/cpu/sample" + str(sample) + "/" + str(frame) + "/*-kActIdentity_output.txt", "./cpu/sample" + str(sample) + "/" + str(frame)])
    #convert_and_write_to_csv(0, 3, [42, 66, 54, 30, 122, 143, 186, 164, 217, 238, 259, 281, 312, 333, 354, 376, 407, 428, 449, 470, 502, 523, 544, 566], "ln_ip.csv")
    if parse_graph == 'true':
        graph = parse_dot(dot_file_path)
        print(graph.get_affine_layer_map()[144].get_oscale())
        print(graph.get_affine_layer_map()[144].get_wscale())

        with open(result_filename, 'w', newline="\n") as csvfile:
            layerwriter = csv.writer(csvfile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
            layerwriter.writerow(["Sample Number", "Frame Number ","Layer Number", "Overflow Count", "Underflow Count", "Max GNA value", "Scale Factor", "Max FP32 value", "Mean of Overflowing FP32 values", "Median", "GNA Layer Name", "IR Layer Name"])

        for sample in range(2, 3):
            for frame in [3]:
                gna_layers_op = []
                fp32_layers_op = []
                file_count = 0
                for filename in os.listdir(os.getcwd() + "/" + "gna/" + "sample" + str(sample) + "/" + str(frame)):
                    gna_layers_op.append([])
                    fp32_layers_op.append([])
                    gna_layers_op[file_count].append(filename)
                    fp32_layers_op[file_count].append(filename)

                    with open(os.getcwd() + "/" + "gna/" + "sample" + str(sample) + "/" + str(frame) + "/" + str(filename), 'r') as f:
                        #gna_curr_layer_op = []
                        gna_curr_output_list = []

                        for data in f:
                            order = data.replace("\n", ",").replace('\n','').strip()
                            output = order.split(",") # Can just split by \n?
                            gna_curr_output_list.append(float(output[0])) # GNA data for current frame in gna_output_list

                    with open(os.getcwd() + "/" + "cpu/" + "sample" + str(sample) + "/" + str(frame) + "/" + str(filename), 'r') as f:
                        #fp32_layer_op = []
                        fp32_curr_output_list = []

                        for data in f:
                            order = data.replace("\n", ",").replace('\n','').strip()
                            output = order.split(",") # Can just split by \n?
                            fp32_curr_output_list.append(float(output[0])) # CPU data for current frame in gna_output_list

                    gna_layers_op[file_count].append(len(gna_curr_output_list))
                    gna_layers_op[file_count].append(gna_curr_output_list)
                    fp32_layers_op[file_count].append(len(fp32_curr_output_list))
                    fp32_layers_op[file_count].append(fp32_curr_output_list)
                    file_count += 1
                    assert(len(gna_curr_output_list) == len(fp32_curr_output_list))

                modified_gna_layers_op = []
                for i in range(0, len(gna_layers_op)):
                    curr_gna_layer_op = gna_layers_op[i]
                    curr_cpu_layer_op = fp32_layers_op[i]
                    curr_gna_layer_modified = []
                    curr_gna_layer_modified.append(curr_gna_layer_op[0])
                    curr_gna_layer_modified.append(curr_gna_layer_op[1])
                    curr_gna_layer_modified.append(curr_gna_layer_op[2])
                    modified_layer_data = calc_OF_UF(curr_gna_layer_op, curr_cpu_layer_op, graph)
                    curr_gna_layer_modified.extend(modified_layer_data)
                    modified_gna_layers_op.append(curr_gna_layer_modified)

                for curr_gna_layer in modified_gna_layers_op:
                    layer_number_array = curr_gna_layer[0].split("_")
                    layer_num = int(layer_number_array[0])
                    with open(result_filename, 'a', newline="\n") as csvfile:
                        layerwriter = csv.writer(csvfile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)

                        if( (int(layer_num) not in graph.get_identity_layer_map()) and (int(layer_num) not in graph.get_affine_layer_map())):
                            print("****item missing")
                            print(layer_num)
                        else :
                            layerwriter.writerow([sample, frame, layer_num, str(curr_gna_layer[3]), str(curr_gna_layer[4]),
                                                    str(curr_gna_layer[5]), str(graph.get_identity_wscale_map()[layer_num]),
                                                    str(curr_gna_layer[6]), str(curr_gna_layer[7]), str(curr_gna_layer[8]),
                                                    graph.get_identity_layer_map()[layer_num].get_gna_name(),
                                                    graph.get_identity_layer_map()[layer_num].get_ir_name(),
                                                    graph.get_affine_layer_map()[layer_num - 1].get_ir_name(),
                                                    graph.get_affine_layer_map()[layer_num - 1].get_wscale(),
                                                    graph.get_affine_layer_map()[layer_num - 1].get_oscale()])

        # List of one or more "pydot.Dot" instances deserialized from this file.

if __name__ == "__main__":
    main()
