import math

def dot_product(v1, v2):
    return v1[0] * v2[0] + v1[1] * v2[1]

def vector_add(v1, v2):
    return (v1[0] + v2[0], v1[1] + v2[1])

def vector_subtract(v1, v2):
    return (v1[0] - v2[0], v1[1] - v2[1])

def scalar_multiply(v, scalar):
    return (v[0] * scalar, v[1] * scalar)

def vector_length(v):
    return math.hypot(v[0], v[1])

def normalize_vector(v):
    length = vector_length(v)
    if length == 0:
        return (0, 0)
    return (v[0] / length, v[1] / length)

def distance_between_points(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])
