import sys
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'sahayak_cloud'))
from objects_onnx import ObjectDetector


def detector():
    result = ObjectDetector.__new__(ObjectDetector)
    result.names = ['person','chair']
    return result


def test_letterbox_preserves_aspect_ratio_and_rgb_channels():
    image = np.zeros((100,200,3),dtype=np.uint8)
    image[:] = (10,20,30)
    blob, scale, left, top = ObjectDetector.prepare(image)
    assert blob.shape == (1,3,640,640)
    assert (scale,left,top) == (3.2,0,160)
    np.testing.assert_allclose(blob[0,:,320,320],[30/255,20/255,10/255],atol=1e-7)
    np.testing.assert_allclose(blob[0,:,0,0],114/255,atol=1e-7)


def test_nms_suppresses_duplicates_but_preserves_different_classes_and_restores_boxes():
    # Three overlapping predictions, one duplicate person and a separate chair.
    rows = np.array([[320,320,320,160,.9,.1],
                     [321,321,320,160,.8,.1],
                     [320,320,320,160,.1,.85]],dtype=np.float32)
    result = detector().decode(rows.T[None],(100,200,3),3.2,0,160)
    assert [r['label'] for r in result] == ['person','chair']
    assert result[0]['box'] == [50,25,150,75]


def test_empty_predictions_and_out_of_frame_boxes():
    model = detector()
    rows = np.array([[0,0,10,10,.1,.1]],dtype=np.float32)
    assert model.decode(rows.T[None],(100,200,3),3.2,0,160) == []
    rows[0,4] = .8
    assert model.decode(rows.T[None],(100,200,3),3.2,0,160)[0]['box'] == [0,0,1.6,0]
