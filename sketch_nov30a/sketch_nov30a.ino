//HX711 Library
#include "HX711.h"

//Pin connections (DT to Digital 2, SCK to Digital 3)
const int LOADCELL_DOUT_PIN = 2; 
const int LOADCELL_SCK_PIN = 3; 

HX711 scale;

//CALIBRATION FACTOR: This converts raw data to grams.
float CALIBRATION_FACTOR = 445.0; 

void setup() {
  Serial.begin(9600);
  Serial.println("Smart Scale Initializing...");
  
  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);

  //Apply the calibration factor
  scale.set_scale(CALIBRATION_FACTOR); 
  
  //Zero the scale
  scale.tare(); 

  Serial.println("Scale is zeroed. Ready for measurement.");
}

void loop() {
  //averaging to filter noise 
  if (scale.is_ready()) {
    float weight = scale.get_units(30); 

    Serial.print("WEIGHT:");
    Serial.println(weight); 
  } 
  //Wait a moment before the next reading
  delay(200); 
}