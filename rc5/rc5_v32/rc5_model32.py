#!/usr/bin/python
# -*- coding: UTF-8 -*-

import subprocess
import copy
import os
import random


def xor(var1, var2, var3):
    statement = ""
    for i in range(0, len(var1)):
        statement += "ASSERT(BVXOR({}, {}) = {});\n".format(var1[i], var2[i], var3[i])
    return statement


def var_value_assign(var1, var):
    statement = ""
    v = "0bin"
    le = len(var)
    for i in range(0, le):
        v += str(var[le - 1 - i])
    statement += "ASSERT({} = {});\n".format(var1, v)
    return statement


def state_dependent(a, b, c, xor_value, mod_value):
    statement = ""
    statement += "ASSERT(BVXOR({}, {}) = {});\n".format(a, b, xor_value)
    statement += "ASSERT(BVMOD(16, {}, 0bin0000000000010000) = {});\n".format(b, mod_value)
    statement1 = "{}".format(xor_value)
    st = ["0000", "0001", "0010", "0011", "0100", "0101", "0110", "0111",
          "1000", "1001", "1010", "1011", "1100", "1101", "1110", "1111"]
    for i in range(1, 16):
        iv = "0bin000000000000"
        sv = "{}[{}:{}]@{}[{}:{}]".format(xor_value, 15 - i, 0, xor_value, 15, 15 - i + 1)
        statement1 = "(IF {} = {}{} THEN {} ELSE {} ENDIF)".format(mod_value, iv, st[i], sv, statement1)
    statement += "ASSERT({} = {});\n".format(c, statement1)
    return statement


def header(var1):
    temp1 = ""
    temp = ""
    for i in range(0, len(var1)):
        temp += "{}, ".format(var1[i])
    temp = temp[0:-2]
    temp += " : BITVECTOR(16);\n"
    temp1 += temp
    return temp1


def trailer(v1, va2):
    return "QUERY(FALSE);\nCOUNTEREXAMPLE;"


def state_var_dec(var, round_index, mul):
    return ["p_{}_{}_{}".format(i, var, round_index) for i in range(0, mul)]


def diff_var_dec(var, round_index):
    return "d_{}_{}".format(var, round_index)


def key_var_dec(var, round_index, mul):
    return ["k_{}_{}_{}".format(i, var, round_index) for i in range(0, mul)]


def solver(solve_file):
    stp_parameters = ["stp", "--minisat", "--CVC", solve_file]
    res = subprocess.check_output(stp_parameters)
    res = res.replace("\r", "")[0:-1]
    print(res)
    if res == "Valid.":
        return True
    else:
        return False


def solver1(solve_file):
    stp_parameters = ["stp", "--minisat", "--CVC", solve_file]
    res = subprocess.check_output(stp_parameters)
    res = res.replace("\r", "")[0:-1]
    return res


def values_propagate_phrase0(cd, round_inf):
    statement = ""
    all_var = []
    key_var = []
    x = state_var_dec("x", round_inf[0], cd["mul"])
    y = state_var_dec("y", round_inf[0], cd["mul"])
    begin_values = list()
    for vi in range(0, cd["mul"]):
        begin_values.append("{}@{}".format(y[vi], x[vi]))

    for rou in range(round_inf[0], round_inf[1]):
        all_var += copy.deepcopy(x)
        all_var += copy.deepcopy(y)

        z = state_var_dec("z", rou, cd["mul"])
        all_var += copy.deepcopy(z)

        u = state_var_dec("u", rou, cd["mul"])
        all_var += copy.deepcopy(u)

        mod0 = state_var_dec("mo0", rou, cd["mul"])
        all_var += copy.deepcopy(mod0)

        for i in range(0, cd["mul"]):
            statement += state_dependent(y[i], x[i], u[i], z[i], mod0[i])

        x1 = state_var_dec("x", rou + 1, cd["mul"])
        y1 = state_var_dec("y", rou + 1, cd["mul"])

        kk0 = key_var_dec("k0", rou, cd["mul"])
        key_var.append(kk0)
        all_var += copy.deepcopy(kk0)
        for i in range(0, cd["mul"]):

            statement += "ASSERT(BVPLUS(16, {}, {}) = {});\n".format(u[i], kk0[i], x1[i])
            statement += "ASSERT({} = {});\n".format(x[i], y1[i])

        x = copy.deepcopy(x1)
        y = copy.deepcopy(y1)
    all_var += copy.deepcopy(x)
    all_var += copy.deepcopy(y)
    end_values = list()
    for vi in range(0, cd["mul"]):
        end_values.append("{}@{}".format(y[vi], x[vi]))

    return begin_values, end_values, key_var, all_var, statement


def __mb_mode1(cd, mode):
    statement = ""

    begin_values, end_values, key_var, all_var, statement1 = values_propagate_phrase0(cd, [mode[1][0], mode[1][1]])
    statement2 = ""
    for i in range(1, cd["mul"]):
        dx0 = "{}@{}".format(diff_var_dec("{}_y".format(i), mode[1][0]), diff_var_dec("{}_x".format(i), mode[1][0]))
        dxn = "{}@{}".format(diff_var_dec("{}_y".format(i), mode[1][1]), diff_var_dec("{}_x".format(i), mode[1][1]))
        all_var.append(diff_var_dec("{}_x".format(i), mode[1][0]))
        all_var.append(diff_var_dec("{}_y".format(i), mode[1][0]))

        all_var.append(diff_var_dec("{}_x".format(i), mode[1][1]))
        all_var.append(diff_var_dec("{}_y".format(i), mode[1][1]))

        statement2 += "ASSERT(BVXOR({}, {}) = {});\n".format(begin_values[0], begin_values[i], dx0)
        statement2 += var_value_assign(dx0, cd["b{}".format(i)])
        statement2 += "ASSERT(BVXOR({}, {}) = {});\n".format(end_values[0], end_values[i], dxn)
        statement2 += var_value_assign(dxn, cd["e{}".format(i)])
    statement += header(all_var)
    statement += statement1
    statement += statement2
    for kv in key_var:
        for i in range(1, cd["mul"]):
            statement += "ASSERT({} = {});\n".format(kv[i], kv[0])
    statement += trailer([], [])
    f = open(cd["solve_file"], "a")
    f.write(statement)
    f.close()


def model_build(cd, mode):
    if os.path.exists(cd["solve_file"]):
        os.remove(cd["solve_file"])
    if mode[0] == 1:
        __mb_mode1(cd, mode)
