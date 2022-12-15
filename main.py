"""
DEMO of few shot learning:
    connect to the camera and prints prediction in an interface
    press :
    1, 2, 3... : the program will register the current image as an instance of the given class
    i : will start inference
    q : quit the program
"""

import time
import cv2
import numpy as np
import cProfile

from demo.graphical_interface import OpencvInterface
from few_shot_model.few_shot_model import FewShotModel
from torch_evaluation.backbone_loader import get_model
from few_shot_model.data_few_shot import DataFewShot

print("import done")



# def get_camera_preprocess():
#     """
#     preprocess a given image into a Tensor (rescaled and center crop + normalized)
#         Args :
#             img(PIL Image or numpy.ndarray): Image to be prepocess.
#         returns :
#             img(torch.Tensor) : preprocessed Image
#     """
#     norm = transforms.Normalize(
#         np.array([x / 255.0 for x in [125.3, 123.0, 113.9]]),
#         np.array([x / 255.0 for x in [63.0, 62.1, 66.7]]),
#     )
#     all_transforms = transforms.Compose(
#         [
#             transforms.ToTensor(),
#             transforms.Resize(110),
#             transforms.CenterCrop(100),
#             norm,
#         ]
#     )

#     return all_transforms


def preprocess(img,dtype=np.float32,shape_input=(84,84)):
    """
    Args: 
        img(np.ndarray(h,w,c)) : 
    """
    assert len(img.shape)==3
    assert img.shape[-1]==3
    print(img.shape)

    img=img.astype(dtype)
    img=cv2.resize(img,dsize=shape_input,interpolation=cv2.INTER_CUBIC)
    img=img[None,:]
    return (img/255-np.array([0.485, 0.456, 0.406],dtype=dtype))/ np.array([0.229, 0.224, 0.225],dtype=dtype)

# addr_cam = "rtsp://admin:brain2021@10.29.232.40"
# cap = cv2.VideoCapture(addr_cam)

# constant of the program
SCALE = 1
RES_OUTPUT = (1920, 1080)  # resolution = (1280,720)
FONT = cv2.FONT_HERSHEY_SIMPLEX

# model constant
# BACKBONE_SPECS = {
#     "model_name": "resnet12",
#     "path": "weight/tieredlong1.pt1",
#     "device":"cuda:0",
#     "type":"pytorch_batch",
#     "kwargs": {
#         "feature_maps": 64,
#         "input_shape": [3, 84, 84],
#         "num_classes": 351,  # 64
#         "few_shot": True,
#         "rotations": False,
#     },
# }


BACKBONE_SPECS = {
    "type":"tensil_model"
    "path_bit":"",
    "path_tmodel":""

}

# model parameters
CLASSIFIER_SPECS = {"model_name": "knn", "kwargs": {"number_neighboors": 5}}
#DEFAULT_TRANSFORM = get_camera_preprocess()


def launch_demo():
    """
    initialize the variable and launch the demo
    """

    #preprocess=get_camera_preprocess()#TODO : update this
    backbone=get_model(BACKBONE_SPECS)#TODO : update this
    few_shot_model = FewShotModel(CLASSIFIER_SPECS)


    # program related constant
    do_inference = False
    do_registration = False
    do_reset = False
    prev_frame_time = time.time()

    possible_input = list(range(177, 185))
    class_num = len(possible_input)
    # time related variables
    clock = 0
    clock_m = 0
    clock_init = 20

    # data holding variables

    current_data = DataFewShot(class_num)

    # CV2 related constant
    cap = cv2.VideoCapture(0)
    cv_interface = OpencvInterface(cap, SCALE, RES_OUTPUT, FONT, class_num)

    while True:
        cv_interface.read_frame()

        new_frame_time = time.time()
        # print('clock: ', clock)
        fps = int(1 / (new_frame_time - prev_frame_time))
        prev_frame_time = new_frame_time

        if clock_m <= clock_init:
            frame = cv_interface.get_image()
            frame=preprocess(frame)
            features = backbone(frame)#TODO : update this

            current_data.add_mean_repr(features)
            if clock_m == clock_init:
                current_data.aggregate_mean_rep()

            cv_interface.put_text("Initialization")
            clock_m += 1

        key = cv_interface.get_key()

        #print(current_data.shot_list)
        # shot acquisition
        if (
            (key in possible_input or do_registration)
            and clock_m > clock_init
            and not do_reset
        ):
            do_inference = False

            if key in possible_input:
                classe = possible_input.index(key)
                last_detected = clock * 1  # time.time()

            print("class :", classe)
            frame = cv_interface.get_image()

            if key in possible_input:
                print(f"saving snapshot of class {classe}")
                cv_interface.add_snapshot(classe)

            # add the representation to the class
            frame=preprocess(frame)#TODO : update this
            features = backbone(frame)

            print("features shape:", features.shape)

            current_data.add_repr(classe, features)

            if abs(clock - last_detected) < 10:
                do_registration = True
                text = f"Class :{classe} registered. \
                Number of shots: {cv_interface.get_number_snapshot(classe)}"
                cv_interface.put_text(text)
            else:
                do_registration = False

        # reset action
        if key == ord("r"):
            do_registration = False
            do_inference = False
            current_data.reset()
            cv_interface.reset_snapshot()
            reset_clock = 0
            do_reset = True

        if do_reset:
            cv_interface.put_text("Resnet background inference")
            reset_clock += 1
            if reset_clock > 20:
                do_reset = False

        # inference action
        if key == ord("i") and current_data.is_data_recorded():
            print("doing inference")
            do_inference = True
            probabilities = None

        # perform inference
        if do_inference and clock_m > clock_init and not do_reset:
            frame = cv_interface.get_image()
            frame=preprocess(frame)#TODO : update this
            features=backbone(frame)
            classe_prediction, probabilities = few_shot_model.predict_class_moving_avg(
                features, probabilities,
                current_data.get_shot_list(),
                current_data.get_mean_features()
            )

            print("probabilities after exp moving average:", probabilities)
            cv_interface.put_text(f"Object is from class :{classe_prediction}")
            # f'Probabilities :{list(map(lambda x:np.round(x, 2), probabilities.tolist()))}'
            cv_interface.draw_indicator(probabilities)

        # interface
        cv_interface.put_text(f"fps:{fps}", bottom_pos_x=0.05, bottom_pos_y=0.1)
        cv_interface.put_text(f"clock:{clock}", bottom_pos_x=0.8, bottom_pos_y=0.1)
        cv_interface.show()

        clock += 1

        if key == ord("q"):
            break
    cv_interface.close()

launch_demo()