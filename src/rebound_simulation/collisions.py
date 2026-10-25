import math
import pathlib
import sys

# -- Source files --
current_dir = pathlib.Path(__file__).resolve()
parent_dir  = current_dir.parent.parent

sys.path.insert(0, str(parent_dir))

import vectors as vec


# -- Geometry helpers --

def get_line_normal(point1, point2):
    dx = point2[0] - point1[0]
    dy = point2[1] - point1[1]

    normal = (-dy, dx)

    length = math.hypot(normal[0], normal[1])
    if length == 0:
        return (0, 0)
    return (normal[0] / length, normal[1] / length)


def distance_point_to_line(point, p1, p2):
    ax = point[0] - p1[0]
    ay = point[1] - p1[1]
    cx = p2[0] - p1[0]
    cy = p2[1] - p1[1]

    length_sq = cx * cx + cy * cy
    if length_sq == 0:
        return vec.distance_between_points(point, p1), p1

    t = max(0.0, min(1.0, (ax * cx + ay * cy) / length_sq))

    closest = (p1[0] + t * cx, p1[1] + t * cy)
    return vec.distance_between_points(point, closest), closest


# -- Circle–circle collisions --

def check_circle_collisions(moving_objects):
    collisions = []
    moving_list = list(moving_objects)

    for i in range(len(moving_list)):
        for j in range(i + 1, len(moving_list)):
            obj1 = moving_list[i]
            obj2 = moving_list[j]

            c1 = obj1.get_center()
            c2 = obj2.get_center()
            r1 = obj1.get_width() / 2
            r2 = obj2.get_width() / 2

            dist = vec.distance_between_points(c1, c2)

            if dist < r1 + r2:
                normal = ((c2[0] - c1[0]) / dist,
                        (c2[1] - c1[1]) / dist)

                collisions.append((obj1, obj2, normal))

    return collisions


def resolve_circle_collisions(collisions, elasticity):
    resolved_pairs = set()

    for obj1, obj2, normal in collisions:
        pair_id = tuple(sorted([id(obj1), id(obj2)]))
        if pair_id in resolved_pairs:
            continue
        resolved_pairs.add(pair_id)

        m1 = obj1.get_mass()
        m2 = obj2.get_mass()
        v1 = (obj1.get_velocity_x(), obj1.get_velocity_y())
        v2 = (obj2.get_velocity_x(), obj2.get_velocity_y())

        # velocity impulse (only if approaching)
        v_rel_along_normal = vec.dot_product(vec.vector_subtract(v1, v2), normal)
        if v_rel_along_normal <= 0:
            continue

        # J = -(1+e) * v_rel_n / (1/m1 + 1/m2)
        J = -(1 + elasticity) * v_rel_along_normal / (1 / m1 + 1 / m2)
        new_v1 = vec.vector_add(v1, vec.scalar_multiply(normal, J / m1))
        new_v2 = vec.vector_subtract(v2, vec.scalar_multiply(normal, J / m2))

        obj1.set_velocity_x(new_v1[0])
        obj1.set_velocity_y(new_v1[1])
        obj2.set_velocity_x(new_v2[0])
        obj2.set_velocity_y(new_v2[1])


# -- Circle–wall collisions --

def check_wall_collisions(moving_objects, static_objects):
    collisions = []

    for moving_obj in moving_objects:
        center = moving_obj.get_center()
        radius = moving_obj.get_width() / 2

        for static_obj in static_objects:
            for p1, p2 in static_obj.edges:
                dist, closest = distance_point_to_line(center, p1, p2)

                if dist > radius:
                    continue

                normal = get_line_normal(p1, p2)
                to_circle = (center[0] - closest[0], center[1] - closest[1])

                # flip normal if it points away from the circle
                if vec.dot_product(normal, to_circle) < 0:
                    normal = (-normal[0], -normal[1])

                collisions.append((moving_obj, static_obj, normal))

    return collisions


def resolve_wall_collisions(collisions):
    for moving_obj, static_obj, normal in collisions:
        velocity = (moving_obj.get_velocity_x(), moving_obj.get_velocity_y())
        v_dot_n = vec.dot_product(velocity, normal)
        elasticity = static_obj.get_elasticity()

        # only process collision if moving into wall
        if v_dot_n >= 0:
            continue  # already separating, no impulse needed

        # apply impulse: Δv = -(1+e) * (v·n) * n
        J = vec.scalar_multiply(normal, -(1 + elasticity) * v_dot_n)
        new_velocity = vec.vector_add(velocity, J)

        moving_obj.set_velocity_x(new_velocity[0])  
        moving_obj.set_velocity_y(new_velocity[1])