# Author: RD7
# Purpose: Define landmarks from mediapipe facemesh
# Created: 2025-10-05

from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Iterable, Iterator, Mapping, Tuple


LEFT_RIGHT_PAIRS = [
    (3, 248), (7, 249), (20, 250), (21, 251), (22, 252), (23, 253), (24, 254),
    (25, 255), (26, 256), (27, 257), (28, 258), (29, 259), (30, 260), (31, 261),
    (32, 262), (33, 263), (34, 264), (35, 265), (36, 266), (37, 267), (38, 268),
    (39, 269), (40, 270), (41, 271), (42, 272), (43, 273), (44, 274), (45, 275),
    (46, 276), (47, 277), (48, 278), (49, 279), (50, 280), (51, 281), (52, 282),
    (53, 283), (54, 284), (55, 285), (56, 286), (57, 287), (58, 288), (59, 289),
    (60, 290), (61, 291), (62, 292), (63, 293), (64, 294), (65, 295), (66, 296),
    (67, 297), (68, 298), (69, 299), (70, 300), (71, 301), (72, 302), (73, 303),
    (74, 304), (75, 305), (76, 306), (77, 307), (78, 308), (79, 309), (80, 310),
    (81, 311), (82, 312), (83, 313), (84, 314), (85, 315), (86, 316), (87, 317),
    (88, 318), (89, 319), (90, 320), (91, 321), (92, 322), (93, 323), (95, 324),
    (96, 325), (97, 326), (98, 327), (99, 328), (100, 329), (101, 330),
    (102, 331), (103, 332), (104, 333), (105, 334), (106, 335), (107, 336),
    (108, 337), (109, 338), (110, 339), (111, 340), (112, 341), (113, 342),
    (114, 343), (115, 344), (116, 345), (117, 346), (118, 347), (119, 348),
    (120, 349), (121, 350), (122, 351), (123, 352), (124, 353), (125, 354),
    (126, 355), (127, 356), (128, 357), (129, 358), (130, 359), (131, 360),
    (132, 361), (133, 362), (134, 363), (135, 364), (136, 365), (137, 366),
    (138, 367), (139, 368), (140, 369), (141, 370), (142, 371), (143, 372),
    (144, 373), (145, 374), (146, 375), (147, 376), (148, 377), (149, 378),
    (150, 379), (153, 380), (154, 381), (155, 382), (156, 383), (157, 384),
    (158, 385), (159, 386), (160, 387), (161, 388), (162, 389), (163, 390),
    (165, 391), (166, 392), (167, 393), (169, 394), (170, 395), (171, 396),
    (172, 397), (173, 398), (174, 399), (176, 400), (177, 401), (178, 402),
    (179, 403), (180, 404), (181, 405), (182, 406), (183, 407), (184, 408),
    (185, 409), (186, 410), (187, 411), (188, 412), (189, 413), (190, 414),
    (191, 415), (192, 416), (193, 417), (194, 418), (196, 419), (198, 420),
    (201, 421), (202, 422), (203, 423), (204, 424), (205, 425), (206, 426),
    (207, 427), (208, 428), (209, 429), (210, 430), (211, 431), (212, 432),
    (213, 433), (214, 434), (215, 435), (216, 436), (217, 437), (218, 438),
    (219, 439), (220, 440), (221, 441), (222, 442), (223, 443), (224, 444),
    (225, 445), (226, 446), (227, 447), (228, 448), (229, 449), (230, 450),
    (231, 451), (232, 452), (233, 453), (234, 454), (235, 455), (236, 456),
    (237, 457), (238, 458), (239, 459), (240, 460), (241, 461), (242, 462),
    (243, 463), (244, 464), (245, 465), (246, 466), (247, 467)
]

MIDLINE_INDICES = [
    0, 1, 2, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 94, 151,
    152, 164, 168, 175, 195, 197, 199, 200
]

LEFT_INDICES = tuple(idx for idx, _ in LEFT_RIGHT_PAIRS)
RIGHT_INDICES = tuple(idx for _, idx in LEFT_RIGHT_PAIRS)
LEFT_LANDMARKS = frozenset(LEFT_INDICES)
RIGHT_LANDMARKS = frozenset(RIGHT_INDICES)
MIDLINE_LANDMARKS = frozenset(MIDLINE_INDICES)
ALL_LANDMARKS = frozenset(range(468))

FACE_OUTLINE = frozenset({
    10, 21, 54, 58, 67, 93, 103, 109, 127, 132, 136, 148,
    149, 150, 152, 162, 172, 176, 234, 251, 284, 288, 297, 323,
    332, 338, 356, 361, 365, 377, 378, 379, 389, 397, 400, 454,
})

FOREHEAD = frozenset({
    8, 9, 10, 21, 52, 53, 54, 55, 63, 65, 66, 67,
    68, 69, 70, 71, 103, 104, 105, 107, 108, 109, 151, 162,
    251, 282, 283, 284, 285, 293, 295, 296, 297, 298, 299, 300,
    301, 332, 333, 334, 336, 337, 338, 389,
})

CHIN = frozenset({
    58, 136, 148, 149, 150, 152, 172, 176, 288, 365, 377, 378,
    379, 397, 400,
})

NOSE = frozenset({
    1, 2, 4, 5, 6, 19, 45, 48, 64, 94, 97, 98,
    115, 168, 195, 197, 220, 275, 278, 294, 326, 327, 344, 440,
})

MOUTH_OUTER_UPPER = frozenset({
    0, 37, 39, 40, 185, 267, 269, 270, 291, 409,
})

MOUTH_OUTER_LOWER = frozenset({
    17, 61, 84, 91, 146, 181, 314, 321, 375, 405,
})

MOUTH_INNER_UPPER = frozenset({
    13, 80, 81, 82, 191, 308, 310, 311, 312, 415,
})

MOUTH_INNER_LOWER = frozenset({
    14, 78, 87, 88, 95, 178, 317, 318, 324, 402,
})

LEFT_EYE = frozenset({
    249, 263, 362, 373, 374, 380, 381, 382, 384, 385, 386, 387,
    388, 390, 398, 466,
})

LEFT_EYE_UPPER_LID = frozenset({
    263, 384, 385, 386, 387, 388, 398, 466,
})

LEFT_EYE_LOWER_LID = frozenset({
    249, 362, 373, 374, 380, 381, 382, 390,
})

RIGHT_EYE = frozenset({
    7, 33, 133, 144, 145, 153, 154, 155, 157, 158, 159, 160,
    161, 163, 173, 246,
})

RIGHT_EYE_UPPER_LID = frozenset({
    33, 157, 158, 159, 160, 161, 173, 246,
})

RIGHT_EYE_LOWER_LID = frozenset({
    7, 133, 144, 145, 153, 154, 155, 163,
})

LEFT_EYEBROW = frozenset({
    276, 282, 283, 285, 293, 295, 296, 300, 334, 336,
})

LEFT_EYEBROW_UPPER = frozenset({
    293, 295, 296, 334, 336,
})

LEFT_EYEBROW_LOWER = frozenset({
    276, 282, 283, 285, 300,
})

RIGHT_EYEBROW = frozenset({
    46, 52, 53, 55, 63, 65, 66, 70, 105, 107,
})

RIGHT_EYEBROW_UPPER = frozenset({
    63, 65, 66, 105, 107,
})

RIGHT_EYEBROW_LOWER = frozenset({
    46, 52, 53, 55, 70,
})

LEFT_IRIS = frozenset({
    474, 475, 476, 477,
})

RIGHT_IRIS = frozenset({
    469, 470, 471, 472,
})

LEFT_CHEEK = frozenset({
    22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 34, 35,
    36, 41, 42, 47, 49, 50, 56, 57, 59, 62, 73, 74,
    75, 76, 77, 89, 92, 93, 96, 100, 101, 102, 110, 111,
    112, 113, 114, 116, 117, 118, 119, 120, 121, 123, 124, 126,
    127, 128, 129, 130, 131, 132, 137, 139, 142, 143, 147, 156,
    162, 165, 166, 177, 183, 184, 186, 187, 189, 190, 192, 198,
    203, 205, 206, 207, 209, 213, 215, 216, 217, 218, 219, 221,
    222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233,
    234, 235, 240, 243, 244, 245, 247,
})

RIGHT_CHEEK = frozenset({
    252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 264, 265,
    266, 271, 272, 277, 279, 280, 286, 287, 289, 292, 303, 304,
    305, 306, 307, 319, 322, 323, 325, 329, 330, 331, 339, 340,
    341, 342, 343, 345, 346, 347, 348, 349, 350, 352, 353, 355,
    356, 357, 358, 359, 360, 361, 366, 368, 371, 372, 376, 383,
    389, 391, 392, 401, 407, 408, 410, 411, 413, 414, 416, 420,
    423, 425, 426, 427, 429, 433, 435, 436, 437, 438, 439, 441,
    442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453,
    454, 455, 460, 463, 464, 465, 467,
})

MOUTH_UPPER = MOUTH_OUTER_UPPER | MOUTH_INNER_UPPER
MOUTH_LOWER = MOUTH_OUTER_LOWER | MOUTH_INNER_LOWER
MOUTH_ALL = MOUTH_UPPER | MOUTH_LOWER
LEFT_EYE_COMPLEX = LEFT_EYE | LEFT_EYEBROW | LEFT_IRIS
RIGHT_EYE_COMPLEX = RIGHT_EYE | RIGHT_EYEBROW | RIGHT_IRIS
EYES_ALL = LEFT_EYE_COMPLEX | RIGHT_EYE_COMPLEX
CHEEKS_ALL = LEFT_CHEEK | RIGHT_CHEEK


@dataclass(frozen=True)
class LandmarkNode:
    indices: FrozenSet[int]
    children: Mapping[str, "LandmarkNode"] = field(default_factory=dict)


def _node(indices: Iterable[int], *, children: Mapping[str, LandmarkNode] | None = None) -> LandmarkNode:
    return LandmarkNode(indices=frozenset(indices), children={} if children is None else dict(children))


LANDMARK_TREE = _node(
    ALL_LANDMARKS,
    children={
        "midline": _node(MIDLINE_LANDMARKS),
        "sides": _node(
            LEFT_LANDMARKS | RIGHT_LANDMARKS,
            children={
                "left": _node(LEFT_LANDMARKS),
                "right": _node(RIGHT_LANDMARKS),
            },
        ),
        "face_outline": _node(FACE_OUTLINE),
        "forehead": _node(FOREHEAD),
        "eyes": _node(
            EYES_ALL,
            children={
                "left": _node(
                    LEFT_EYE_COMPLEX,
                    children={
                        "eye": _node(
                            LEFT_EYE,
                            children={
                                "upper_lid": _node(LEFT_EYE_UPPER_LID),
                                "lower_lid": _node(LEFT_EYE_LOWER_LID),
                            },
                        ),
                        "eyebrow": _node(
                            LEFT_EYEBROW,
                            children={
                                "upper_ridge": _node(LEFT_EYEBROW_UPPER),
                                "lower_ridge": _node(LEFT_EYEBROW_LOWER),
                            },
                        ),
                        "iris": _node(LEFT_IRIS),
                    },
                ),
                "right": _node(
                    RIGHT_EYE_COMPLEX,
                    children={
                        "eye": _node(
                            RIGHT_EYE,
                            children={
                                "upper_lid": _node(RIGHT_EYE_UPPER_LID),
                                "lower_lid": _node(RIGHT_EYE_LOWER_LID),
                            },
                        ),
                        "eyebrow": _node(
                            RIGHT_EYEBROW,
                            children={
                                "upper_ridge": _node(RIGHT_EYEBROW_UPPER),
                                "lower_ridge": _node(RIGHT_EYEBROW_LOWER),
                            },
                        ),
                        "iris": _node(RIGHT_IRIS),
                    },
                ),
            },
        ),
        "nose": _node(NOSE),
        "cheeks": _node(
            CHEEKS_ALL,
            children={
                "left": _node(LEFT_CHEEK),
                "right": _node(RIGHT_CHEEK),
            },
        ),
        "mouth": _node(
            MOUTH_ALL,
            children={
                "upper_lip": _node(
                    MOUTH_UPPER,
                    children={
                        "outer": _node(MOUTH_OUTER_UPPER),
                        "inner": _node(MOUTH_INNER_UPPER),
                    },
                ),
                "lower_lip": _node(
                    MOUTH_LOWER,
                    children={
                        "outer": _node(MOUTH_OUTER_LOWER),
                        "inner": _node(MOUTH_INNER_LOWER),
                    },
                ),
            },
        ),
        "chin": _node(CHIN),
    },
)


def get_group(path: Iterable[str]) -> LandmarkNode:
    """Navigate the landmark tree with an iterable path."""
    keys = tuple(path)
    node = LANDMARK_TREE
    if keys and keys[0] == "face":
        keys = keys[1:]
    for key in keys:
        node = node.children[key]
    return node


def get_indices(path: Iterable[str]) -> FrozenSet[int]:
    """Return the landmark indices associated with the given path."""
    return get_group(path).indices


def iter_groups(
    node: LandmarkNode | None = None,
    prefix: Tuple[str, ...] = ("face",),
) -> Iterator[Tuple[Tuple[str, ...], FrozenSet[int]]]:
    """Yield (path, indices) pairs for every node in the tree."""
    current = LANDMARK_TREE if node is None else node
    yield prefix, current.indices
    for name, child in current.children.items():
        yield from iter_groups(child, prefix + (name,))


LANDMARK_GROUP_LOOKUP = {
    "/".join(path): indices for path, indices in iter_groups()
}

__all__ = [
    "ALL_LANDMARKS",
    "CHEEKS_ALL",
    "CHIN",
    "FACE_OUTLINE",
    "FOREHEAD",
    "LANDMARK_GROUP_LOOKUP",
    "LANDMARK_TREE",
    "LEFT_CHEEK",
    "LEFT_EYE",
    "LEFT_EYE_COMPLEX",
    "LEFT_EYE_LOWER_LID",
    "LEFT_EYE_UPPER_LID",
    "LEFT_EYEBROW",
    "LEFT_EYEBROW_LOWER",
    "LEFT_EYEBROW_UPPER",
    "LEFT_INDICES",
    "LEFT_IRIS",
    "LEFT_LANDMARKS",
    "LEFT_RIGHT_PAIRS",
    "MIDLINE_INDICES",
    "MIDLINE_LANDMARKS",
    "MOUTH_ALL",
    "MOUTH_INNER_LOWER",
    "MOUTH_INNER_UPPER",
    "MOUTH_LOWER",
    "MOUTH_OUTER_LOWER",
    "MOUTH_OUTER_UPPER",
    "MOUTH_UPPER",
    "NOSE",
    "RIGHT_CHEEK",
    "RIGHT_EYE",
    "RIGHT_EYE_COMPLEX",
    "RIGHT_EYE_LOWER_LID",
    "RIGHT_EYE_UPPER_LID",
    "RIGHT_EYEBROW",
    "RIGHT_EYEBROW_LOWER",
    "RIGHT_EYEBROW_UPPER",
    "RIGHT_INDICES",
    "RIGHT_IRIS",
    "RIGHT_LANDMARKS",
    "get_group",
    "get_indices",
    "iter_groups",
    "FaceMeshDetector",
]
