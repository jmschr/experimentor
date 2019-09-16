from examples.track.models import MyCamera, MyDAQ
from examples.track.measurements import Track


from experimentor import Experiment


app = Experiment()
app.register_models(MyCamera, MyDAQ)
app.register_measurements(Track)

app._measurements[0].timelapse()
