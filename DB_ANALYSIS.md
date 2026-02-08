# RIDB Database Deep Analysis

Generated from `ridb.db` (261 MB) — raw analysis, no assumptions.
All 132,974 campsites, 15,061 facilities, 2.4M attributes, 432K equipment records.

```

================================================================================
  1. DATABASE OVERVIEW
================================================================================
Tables: 16
  activities                    :          154
  campsite_attributes           :    2,423,061
  campsite_equipment            :      431,992
  campsites                     :      132,974
  events                        :            0
  facilities                    :       15,061
  facility_activities           :       48,795
  facility_addresses            :       16,328
  links                         :       64,550
  media                         :       32,500
  organizations                 :           33
  permit_entrances              :          857
  rec_area_activities           :            0
  rec_area_addresses            :        3,878
  rec_areas                     :        3,671
  tours                         :            0

DB file: 261.0 MB

================================================================================
  2. FACILITIES - Shape of the data
================================================================================
Column completeness (non-null, non-empty):
  facility_id                        :   15,061 / 15,061  (100.0%)
  facility_name                      :   15,053 / 15,061  ( 99.9%)
  facility_type                      :   15,061 / 15,061  (100.0%)
  facility_description               :   14,267 / 15,061  ( 94.7%)
  facility_directions                :    8,297 / 15,061  ( 55.1%)
  facility_phone                     :    6,592 / 15,061  ( 43.8%)
  facility_email                     :    4,288 / 15,061  ( 28.5%)
  facility_latitude                  :   15,061 / 15,061  (100.0%)
  facility_longitude                 :   15,061 / 15,061  (100.0%)
  facility_reservation_url           :      102 / 15,061  (  0.7%)
  facility_map_url                   :      326 / 15,061  (  2.2%)
  facility_use_fee                   :    2,103 / 15,061  ( 14.0%)
  facility_ada_access                :    4,764 / 15,061  ( 31.6%)
  facility_accessibility_text        :      253 / 15,061  (  1.7%)
  reservable                         :   15,061 / 15,061  (100.0%)
  enabled                            :   15,061 / 15,061  (100.0%)
  stay_limit                         :      334 / 15,061  (  2.2%)
  keywords                           :    4,805 / 15,061  ( 31.9%)
  parent_org_id                      :   15,061 / 15,061  (100.0%)
  parent_rec_area_id                 :   14,279 / 15,061  ( 94.8%)
  legacy_facility_id                 :    4,816 / 15,061  ( 32.0%)
  last_updated                       :   15,061 / 15,061  (100.0%)

Facility types:
  Facility                           :    8,173
  Campground                         :    5,630
  Activity Pass                      :      537
  Visitor Center                     :      248
  Permit                             :      145
  Ticket Facility                    :      134
  Tree Permit                        :       82
  Timed Entry                        :       35
  Venue Reservations                 :       32
  Cemetery and Memorial              :       24
  Library                            :        9
  National Fish Hatchery             :        3
  Museum                             :        3
  Archives                           :        3
  Kiosk                              :        1
  Federal                            :        1
  Construction Camp site             :        1

Enabled status:
  enabled=1: 15,061

Reservable:
  reservable=0: 9,304
  reservable=1: 5,757

Reservable by facility type:
  Facility                 :      0 /  8,173 reservable (0.0%)
  Campground               :  4,792 /  5,630 reservable (85.1%)
  Activity Pass            :    537 /    537 reservable (100.0%)
  Visitor Center           :      0 /    248 reservable (0.0%)
  Permit                   :    145 /    145 reservable (100.0%)
  Ticket Facility          :    134 /    134 reservable (100.0%)
  Tree Permit              :     82 /     82 reservable (100.0%)
  Timed Entry              :     35 /     35 reservable (100.0%)
  Venue Reservations       :     32 /     32 reservable (100.0%)
  Cemetery and Memorial    :      0 /     24 reservable (0.0%)
  Library                  :      0 /      9 reservable (0.0%)
  National Fish Hatchery   :      0 /      3 reservable (0.0%)
  Museum                   :      0 /      3 reservable (0.0%)
  Archives                 :      0 /      3 reservable (0.0%)
  Kiosk                    :      0 /      1 reservable (0.0%)
  Federal                  :      0 /      1 reservable (0.0%)
  Construction Camp site   :      0 /      1 reservable (0.0%)

================================================================================
  3. FACILITIES - Geographic coverage
================================================================================
Coordinate quality:
  Total: 15,061
  Valid coords: 12,474 (lat/lon both non-zero)
  Zero coords: 2,587
  NULL coords: 0

Latitude range (non-zero):
  Lat: -88.5482 to 69.3625 (avg 39.6832)
  Lon: -172.6471 to 145.7204

Coords outside continental US (lat not 24-50, lon not -125 to -66):
  111 facilities

Facilities by state (top 25):
  CA   :  2,108
  UT   :  1,433
  CO   :  1,199
  WY   :  1,059
  OR   :  1,032
  ID   :    845
  MT   :    623
  AZ   :    581
  WA   :    570
  NM   :    439
  NC   :    426
  AK   :    352
  TX   :    334
  OK   :    272
  AR   :    244
  TN   :    214
  MI   :    209
  GA   :    199
  NV   :    194
  KY   :    176
  SD   :    173
  VA   :    166
  MO   :    142
  MN   :    141
  WV   :    133

States with most zero-coord facilities:
  CA   :    504
  UT   :    389
  WY   :    387
  CO   :    288
  NC   :    244
  OR   :    206
  ID   :    129
  WA   :    109
  MT   :     91
  NM   :     40

================================================================================
  4. FACILITIES <-> CAMPSITES relationship
================================================================================
Facilities total: 15,061
Facilities WITH campsites: 5,172
Facilities WITHOUT campsites: 9,889

Campsites per facility distribution:
  1         :  1,300 facilities (   1,300 campsites)
  2-5       :    859 facilities (   2,977 campsites)
  6-10      :    394 facilities (   3,243 campsites)
  11-25     :  1,014 facilities (  17,617 campsites)
  26-50     :    787 facilities (  28,603 campsites)
  51-100    :    555 facilities (  39,260 campsites)
  101-200   :    223 facilities (  29,918 campsites)
  201-500   :     40 facilities (  10,056 campsites)

Largest facilities by campsite count:
  NPS    Colter Bay Campground                             :   360 sites
  NPS    MATHER CAMPGROUND                                 :   357 sites
  USACE  SHENANGO REC AREA CAMPGROUND                      :   328 sites
  USACE  BLOOMINGTON EAST                                  :   323 sites
  NPS    Gros Ventre Campground                            :   322 sites
  NPS    Tuolumne Meadows Campground                       :   311 sites
  FS     Cemetery Point Picnic Area                        :   310 sites
  USACE  Mill Creek Camping (Berlin Lake)                  :   307 sites
  FS     MERRILL CAMPGROUND                                :   302 sites
  NPS    BLACKWOODS CAMPGROUND                             :   292 sites
  FS     STRAWBERRY BAY                                    :   292 sites
  FS     BROKEN ARROW CAMPGROUND                           :   274 sites
  USACE  SEVEN POINTS (PA)                                 :   267 sites
  NPS    Rocky Mountain National Park Moraine Park Campground:   258 sites
  USACE  PRAIRIE FLOWER RECREATION AREA                    :   252 sites

================================================================================
  5. CAMPSITES - Shape of the data
================================================================================
Column completeness:
  campsite_id              :    132,974 / 132,974  (100.0%)
  facility_id              :    132,974 / 132,974  (100.0%)
  campsite_name            :    132,956 / 132,974  (100.0%)
  campsite_type            :    132,963 / 132,974  (100.0%)
  type_of_use              :    132,974 / 132,974  (100.0%)
  loop                     :    129,478 / 132,974  ( 97.4%)
  campsite_accessible      :      9,026 / 132,974  (  6.8%)
  campsite_reservable      :    100,636 / 132,974  ( 75.7%)
  campsite_latitude        :    107,024 / 132,974  ( 80.5%)
  campsite_longitude       :    107,024 / 132,974  ( 80.5%)
  created_date             :    132,974 / 132,974  (100.0%)
  last_updated             :    132,974 / 132,974  (100.0%)

Type of use:
  Overnight      :  129,955
  Day            :    3,018
  multi          :        1

All campsite types:
  STANDARD NONELECTRIC                         :   60,301
  STANDARD ELECTRIC                            :   33,386
  MANAGEMENT                                   :   10,949
  TENT ONLY NONELECTRIC                        :    9,540
  RV NONELECTRIC                               :    3,298
  RV ELECTRIC                                  :    3,045
  WALK TO                                      :    1,985
  GROUP STANDARD NONELECTRIC                   :    1,270
  EQUESTRIAN NONELECTRIC                       :    1,068
  BOAT IN                                      :      930
  GROUP SHELTER ELECTRIC                       :      817
  CABIN NONELECTRIC                            :      728
  GROUP TENT ONLY AREA NONELECTRIC             :      591
  PARKING                                      :      586
  HIKE TO                                      :      571
  GROUP STANDARD AREA NONELECTRIC              :      548
  PICNIC                                       :      438
  TENT ONLY ELECTRIC                           :      431
  CABIN ELECTRIC                               :      372
  GROUP PICNIC AREA                            :      350
  GROUP SHELTER NONELECTRIC                    :      334
  EQUESTRIAN ELECTRIC                          :      270
  MOORING                                      :      259
  GROUP STANDARD ELECTRIC                      :      235
  OVERNIGHT SHELTER ELECTRIC                   :      150
  SHELTER NONELECTRIC                          :      117
  OVERNIGHT SHELTER NONELECTRIC                :       81
  YURT                                         :       79
  GROUP WALK TO                                :       47
  GROUP RV AREA NONELECTRIC                    :       36
  GROUP EQUESTRIAN                             :       29
  GROUP STANDARD AREA ELECTRIC                 :       26
  Zone                                         :       24
  LOOKOUT                                      :       24
  GROUP HIKE TO                                :       18
  SHELTER ELECTRIC                             :       13
  ANCHORAGE                                    :       13
  NULL                                         :       11
  BALL FIELD                                   :        3
  Designated Campsite                          :        1

Reservable campsites:
  No: 32,338
  Yes: 100,636

Accessible campsites:
  No: 123,948
  Yes: 9,026

Campsite coordinate quality:
  Valid: 107,024
  Zero: 25,950

Loop field (campsite grouping within facility):
  Has loop value: 129,478
  Unique loop names: 5,483

================================================================================
  6. CAMPSITE ATTRIBUTES - Complete inventory
================================================================================
Total attribute records: 2,423,061
Unique attribute names: 341

All attributes by frequency:
  Checkout Time                                :    123,255 records,     83 unique values
  Checkin Time                                 :    123,093 records,     84 unique values
  Max Num of People                            :    120,390 records,     98 unique values
  Max Num of Vehicles                          :    117,108 records,     80 unique values
  Pets Allowed                                 :    113,295 records,      8 unique values
  IS EQUIPMENT MANDATORY                       :    110,562 records,      3 unique values
  Min Num of People                            :    109,925 records,     29 unique values
  Driveway Surface                             :    105,454 records,     13 unique values
  Capacity/Size Rating                         :    105,323 records,     12 unique values
  Max Vehicle Length                           :    103,209 records,    313 unique values
  Driveway Entry                               :    102,366 records,     12 unique values
  Campfire Allowed                             :     95,200 records,      4 unique values
  Shade                                        :     89,341 records,      9 unique values
  Placed on Map                                :     76,172 records,      3 unique values
  Picnic Table                                 :     64,314 records,      4 unique values
  Driveway Length                              :     55,031 records,    564 unique values
  Site Access                                  :     49,827 records,     14 unique values
  Water Hookup                                 :     45,618 records,      7 unique values
  Electricity Hookup                           :     44,424 records,     57 unique values
  Fire Pit                                     :     42,970 records,      3 unique values
  GRILLS                                       :     34,223 records,      3 unique values
  Site Length                                  :     33,904 records,    316 unique values
  Min Num of Vehicles                          :     30,027 records,     14 unique values
  Site Rating                                  :     27,497 records,     10 unique values
  Driveway Grade                               :     26,395 records,      8 unique values
  Site Width                                   :     25,761 records,    188 unique values
  Location Rating                              :     25,446 records,      9 unique values
  Condition Rating                             :     23,834 records,     11 unique values
  CAMPFIRE RINGS                               :     23,044 records,      2 unique values
  PICNIC TABLES                                :     19,977 records,      1 unique values
  Proximity to Water                           :     18,396 records,     10 unique values
  Tent Pad Length                              :     16,034 records,    112 unique values
  BBQ                                          :     15,589 records,      3 unique values
  Tent Pad Width                               :     15,480 records,     91 unique values
  Tent Pad                                     :     13,676 records,      3 unique values
  Site Height/Overhead Clearance               :     10,878 records,     65 unique values
  Sewer Hookup                                 :     10,274 records,      4 unique values
  Base Number of People                        :      9,748 records,     35 unique values
  Base Number of Vehicles                      :      9,171 records,     28 unique values
  Hike In Distance to Site                     :      8,880 records,    589 unique values
  Double Driveway                              :      7,919 records,      6 unique values
  Accessibility                                :      7,052 records,      2 unique values
  Quiet Area                                   :      6,819 records,      3 unique values
  FOOD STORAGE LOCKER                          :      6,586 records,      1 unique values
  LANTERN POSTS                                :      6,370 records,      1 unique values
  FLUSH TOILETS                                :      5,837 records,      1 unique values
  DRINKING WATER                               :      5,577 records,      2 unique values
  PAVED ROADS                                  :      5,063 records,      1 unique values
  VAULT TOILETS                                :      4,899 records,      1 unique values
  TENT PADS                                    :      4,625 records,      2 unique values
  HOST                                         :      4,426 records,      2 unique values
  ELECTRIC HOOKUPS                             :      4,197 records,      1 unique values
  Food Locker                                  :      4,076 records,      3 unique values
  WATER SPIGOT                                 :      4,071 records,      1 unique values
  Shower/Bath Type                             :      3,919 records,      5 unique values
  DUMP STATION                                 :      3,911 records,      2 unique values
  Lantern Pole                                 :      3,770 records,      2 unique values
  WATER HOOKUPS                                :      3,636 records,      1 unique values
  Privacy                                      :      3,604 records,      3 unique values
  PAVED PARKING                                :      3,433 records,      1 unique values
  Accessible Occupant Message                  :      3,338 records,      2 unique values
  BOAT RAMP                                    :      3,191 records,      1 unique values
  SHOWERS                                      :      3,135 records,      1 unique values
  Bed Type                                     :      2,961 records,     20 unique values
  PARKING AREA                                 :      2,748 records,      2 unique values
  TRASH COLLECTION                             :      2,704 records,      1 unique values
  LAKE ACCESS                                  :      2,491 records,      1 unique values
  Max Num of Horses                            :      2,386 records,     23 unique values
  ACCESSIBLE FLUSH TOILETS                     :      2,382 records,      1 unique values
  SELF PAY STATION                             :      2,352 records,      1 unique values
  TRAILHEADS                                   :      2,085 records,      1 unique values
  PAVED SITES                                  :      2,049 records,      1 unique values
  Num of Beds                                  :      1,950 records,     17 unique values
  CELL PHONE SERVICE                           :      1,891 records,      1 unique values
  ACCESSIBLE PARKING                           :      1,887 records,      1 unique values
  DAY USE AREA                                 :      1,867 records,      1 unique values
  FLUSH TOILETS (SEASONAL)                     :      1,843 records,      1 unique values
  ACCESSIBLE SHOWERS                           :      1,838 records,      1 unique values
  ACCESSIBLE CAMPSITES                         :      1,825 records,      1 unique values
  RECYCLING                                    :      1,818 records,      1 unique values
  PLAYGROUND                                   :      1,810 records,      1 unique values
  ENTRANCE STATION                             :      1,802 records,      1 unique values
  Num of Rooms                                 :      1,794 records,     16 unique values
  Full Hookup                                  :      1,778 records,      5 unique values
  Num of Bedrooms                              :      1,741 records,     12 unique values
  PICNIC AREA                                  :      1,740 records,      1 unique values
  Lean To/Shelter                              :      1,734 records,      3 unique values
  BEACH ACCESS                                 :      1,699 records,      1 unique values
  FIREWOOD                                     :      1,625 records,      1 unique values
  AMPHITHEATER                                 :      1,592 records,      1 unique values
  ACCESSIBLE DRINKING WATER                    :      1,546 records,      1 unique values
  DRINKING WATER (PEAK SEASON)                 :      1,515 records,      3 unique values
  WATER (SEASONAL)                             :      1,383 records,      1 unique values
  EMERGENCY PHONE                              :      1,364 records,      2 unique values
  ACCESSIBLE VAULT TOILETS                     :      1,344 records,      1 unique values
  Grills/Fire Ring                             :      1,300 records,      3 unique values
  PICNIC SHELTERS                              :      1,253 records,      1 unique values
  DRINKING WATER (HAND PUMP)                   :      1,233 records,      1 unique values
  ACCESSIBLE GRILLS                            :      1,205 records,      1 unique values
  Platform                                     :      1,114 records,      3 unique values
  BOAT TRAILER PARKING                         :      1,107 records,      1 unique values
  TABLES                                       :      1,099 records,      1 unique values
  BOAT DOCK                                    :      1,086 records,      1 unique values
  RV PARKING                                   :      1,051 records,      1 unique values
  GENERAL STORE                                :      1,004 records,      2 unique values
  ICE                                          :        993 records,      1 unique values
  TABLE & BENCHES                              :        969 records,      1 unique values
  ELECTRICITY                                  :        957 records,      1 unique values
  ACCESSIBLE PICNIC AREA                       :        892 records,      1 unique values
  ACCESSIBLE SITES                             :        878 records,      1 unique values
  CAMPFIRE CIRCLES                             :        849 records,      1 unique values
  ACCESSIBLE PICNIC SHELTERS                   :        836 records,      1 unique values
  VISITOR CENTER                               :        794 records,      2 unique values
  ACCESSIBLE BOAT RAMP                         :        784 records,      1 unique values
  RIVER ACCESS                                 :        777 records,      1 unique values
  LAUNDRY FACILITIES                           :        769 records,      1 unique values
  CAMPFIRE PROGRAMS                            :        758 records,      1 unique values
  ACCESSIBLE PLAYGROUND                        :        754 records,      1 unique values
  PIT TOILETS                                  :        742 records,      1 unique values
  ACCESSIBLE WALKWAYS                          :        725 records,      1 unique values
  TRAILHEAD PARKING                            :        714 records,      1 unique values
  ACCESSIBLE TRAILS                            :        713 records,      1 unique values
  PAVED PATHWAYS                               :        708 records,      1 unique values
  CREEK ACCESS                                 :        685 records,      1 unique values
  UTILITY SINKS                                :        672 records,      1 unique values
  COIN SHOWERS                                 :        665 records,      2 unique values
  MARINA                                       :        658 records,      1 unique values
  SHOWERS (SEASONAL)                           :        614 records,      1 unique values
  ATM                                          :        596 records,      1 unique values
  FISH CLEANING STATIONS                       :        595 records,      1 unique values
  BOAT SLIPS                                   :        561 records,      1 unique values
  Satellite TV Access                          :        552 records,      2 unique values
  WATERFRONT SITES                             :        547 records,      1 unique values
  DOCK                                         :        532 records,      1 unique values
  FIREWOOD VENDER                              :        498 records,      1 unique values
  KAYAK RENTALS                                :        493 records,      1 unique values
  WIRELESS INTERNET                            :        491 records,      1 unique values
  FISHING PIER                                 :        473 records,      1 unique values
  NON-POTABLE WATER                            :        470 records,      1 unique values
  ACCESSIBLE PIT TOILETS                       :        469 records,      1 unique values
  GIFT SHOP                                    :        451 records,      2 unique values
  Horse Stall/Corral                           :        430 records,      3 unique values
  BASKETBALL COURTS                            :        420 records,      1 unique values
  VOLLEYBALL COURTS                            :        414 records,      1 unique values
  RESTAURANT                                   :        390 records,      2 unique values
  OFF-ROAD VEHICLE TRAILS                      :        388 records,      1 unique values
  ACCESSIBLE FISHING DOCK                      :        373 records,      1 unique values
  FISHING LICENSES                             :        369 records,      1 unique values
  HORSESHOE PIT                                :        361 records,      1 unique values
  EMERGENCY SERVICES                           :        359 records,      1 unique values
  LIFEGUARDS                                   :        352 records,      1 unique values
  TENNIS COURTS                                :        351 records,      1 unique values
  SOFTBALL FIELDS                              :        351 records,      1 unique values
  CANOE RENTALS                                :        351 records,      1 unique values
  SOCCER FIELDS                                :        342 records,      1 unique values
  SWIMMING POOL                                :        339 records,      1 unique values
  RECREATION CENTER                            :        339 records,      1 unique values
  CONCESSION (SEASONAL)                        :        334 records,      1 unique values
  VENDING MACHINES                             :        333 records,      1 unique values
  INTERPRETIVE TRAILS                          :        331 records,      1 unique values
  BASEBALL FIELDS                              :        327 records,      1 unique values
  HORSEBACK RIDING TRAILS                      :        318 records,      1 unique values
  BIKE RENTALS                                 :        318 records,      1 unique values
  RANGER STATION                               :        299 records,      1 unique values
  ACCESSIBLE BOCK DOCK                         :        294 records,      1 unique values
  SCENIC OVERLOOKS                             :        285 records,      1 unique values
  BILGE PUMP STATION                           :        266 records,      1 unique values
  WASHER & DRYER                               :        262 records,      1 unique values
  Horse Hitching Post                          :        259 records,      3 unique values
  LIGHTS                                       :        257 records,      1 unique values
  CORRALS                                      :        254 records,      1 unique values
  Non Smoking                                  :        248 records,      2 unique values
  FUEL AVAILABLE                               :        240 records,      1 unique values
  HORSE CORRALS                                :        224 records,      1 unique values
  CONCESSIONS                                  :        216 records,      2 unique values
  Porch                                        :        212 records,      3 unique values
  PAY PHONE                                    :        208 records,      1 unique values
  BOAT STORAGE                                 :        201 records,      1 unique values
  BROOM & DUST PAN                             :        199 records,      1 unique values
  PROPANE                                      :        186 records,      1 unique values
  FIREPLACE                                    :        182 records,      1 unique values
  WOOD STOVE                                   :        177 records,      1 unique values
  Furnished                                    :        174 records,      2 unique values
  Cabin Heating                                :        174 records,      5 unique values
  SECURITY LIGHTS                              :        171 records,      1 unique values
  CHURCH                                       :        171 records,      1 unique values
  HITCHING RACKS                               :        167 records,      1 unique values
  BED(S) WITH MATTRESS                         :        167 records,      1 unique values
  Toilet                                       :        155 records,      2 unique values
  TABLE & CHAIRS                               :        154 records,      1 unique values
  CATEGORY                                     :        153 records,      4 unique values
  MAP NUMBER                                   :        152 records,    150 unique values
  FIRE EXTINGUISHER                            :        147 records,      1 unique values
  BOARDWALK                                    :        146 records,      1 unique values
  CAVE TOURS                                   :        145 records,      1 unique values
  OUTHOUSE                                     :        144 records,      1 unique values
  BUNKBED(S)                                   :        142 records,      1 unique values
  COOKING UTENSILS                             :        140 records,      1 unique values
  Lighting                                     :        134 records,      4 unique values
  COOKING POTS                                 :        134 records,      1 unique values
  PORTABLE TOILETS                             :        132 records,      1 unique values
  COOKING AREA                                 :        131 records,      1 unique values
  CAMPING SUPPLIES                             :        124 records,      1 unique values
  KITCHEN                                      :        123 records,      1 unique values
  FISHING DOCK                                 :        123 records,      1 unique values
  GEOLOGICAL ATTRACTIONS                       :        122 records,      1 unique values
  BOAT RENTALS                                 :        121 records,      1 unique values
  SMOKE ALARM                                  :        119 records,      1 unique values
  Generator Free                               :        118 records,      2 unique values
  Stove/Oven                                   :        114 records,      2 unique values
  Microwave                                    :        112 records,      2 unique values
  Internet Access                              :        107 records,      2 unique values
  Wood Heating                                 :        106 records,      2 unique values
  Woodstove/Fireplace                          :        104 records,      2 unique values
  KENNEL                                       :        102 records,      1 unique values
  COT(S)                                       :        102 records,      1 unique values
  REFRIGERATOR                                 :        100 records,      1 unique values
  PROPANE STOVE                                :         99 records,      1 unique values
  Hot Water                                    :         99 records,      2 unique values
  EDUCATIONAL PROGRAMS                         :         96 records,      1 unique values
  Deck                                         :         90 records,      2 unique values
  OVEN                                         :         89 records,      1 unique values
  Living Room                                  :         88 records,      2 unique values
  HEATING STOVE                                :         85 records,      1 unique values
                                               :         83 records,      4 unique values
  HEATER                                       :         75 records,      1 unique values
  COFFEE POT                                   :         75 records,      1 unique values
  CLOTHES DRYER                                :         75 records,      1 unique values
  MOTOR BOAT RENTALS                           :         74 records,      1 unique values
  Stove/Fridge                                 :         70 records,      3 unique values
  BED(S)                                       :         70 records,      1 unique values
  ICE MACHINE                                  :         67 records,      1 unique values
  FISHING GUIDE                                :         66 records,      1 unique values
  PONTOON RENTAL                               :         64 records,      1 unique values
  Group Allowed                                :         63 records,      1 unique values
  DINING AREA                                  :         63 records,      1 unique values
  PROPANE OVEN                                 :         62 records,      1 unique values
  Fridge                                       :         62 records,      2 unique values
  BUNKBEDS(S) WITH MATTRESSES                  :         62 records,      1 unique values
  Propane Heating                              :         61 records,      2 unique values
  COUCHES                                      :         61 records,      1 unique values
  Fridge with Freezer                          :         58 records,      2 unique values
  SHUTTLE BUS SERVICE                          :         56 records,      1 unique values
  Electric Heating                             :         52 records,      2 unique values
  BAIT SHOP                                    :         51 records,      1 unique values
  PROPANE HEAT                                 :         50 records,      1 unique values
  ELECTRIC STOVE                               :         50 records,      1 unique values
  PROPANE LIGHTS                               :         49 records,      1 unique values
  MOTORCYCLE TRAILS                            :         49 records,      1 unique values
  LANTERN                                      :         49 records,      1 unique values
  Supplies                                     :         47 records,      4 unique values
  SLEEPING SHELTER                             :         47 records,      1 unique values
  MOP                                          :         47 records,      1 unique values
  Clothes-Line                                 :         47 records,      2 unique values
  FUTON(S)                                     :         46 records,      1 unique values
  CLEANING SUPPLIES                            :         46 records,      1 unique values
  Oil Heating                                  :         45 records,      1 unique values
  HISTORIC SITES                               :         45 records,      1 unique values
  MOTEL                                        :         43 records,      1 unique values
  MATTRESS PAD(S)                              :         37 records,      1 unique values
  HORSE STALLS                                 :         37 records,      1 unique values
  AXE                                          :         37 records,      1 unique values
  DVD PLAYER                                   :         35 records,      1 unique values
  CLEANING EQUIPMENT                           :         35 records,      1 unique values
  ACCESSIBLE SCENIC OVERLOOK                   :         35 records,      1 unique values
  HORSE STAGING AREA                           :         34 records,      1 unique values
  PLAYGROIUND                                  :         33 records,      1 unique values
  RV STORAGE                                   :         32 records,      1 unique values
  PROPANE REFRIDGERATOR                        :         32 records,      1 unique values
  ARCHEOLOGICAL SITES                          :         32 records,      1 unique values
  Cable TV Access                              :         30 records,      2 unique values
  BEAR POLE                                    :         30 records,      1 unique values
  Air Conditioning                             :         29 records,      3 unique values
  Manure Disposal                              :         28 records,      1 unique values
  Fax Hookup                                   :         28 records,      2 unique values
  FOOT STORAGE LOCKER                          :         28 records,      1 unique values
  TABLE                                        :         25 records,      1 unique values
  FIRE RING                                    :         25 records,      1 unique values
  WIND SHELTERS                                :         24 records,      1 unique values
  TWIN BED(S)                                  :         24 records,      1 unique values
  Gas Heating                                  :         22 records,      2 unique values
  BATHTUB                                      :         21 records,      1 unique values
  KITCHEN (NO WATER)                           :         20 records,      1 unique values
  STOCK WATERING TANK                          :         19 records,      1 unique values
  OUTDOOR COOLER BOX                           :         19 records,      1 unique values
  HORSE WATERING STATION                       :         19 records,      1 unique values
  EVENT AREA                                   :         18 records,      1 unique values
  WATER TROUGHS                                :         17 records,      1 unique values
  BUCKET & SHOVEL                              :         16 records,      1 unique values
  GROUP COOKING FACILITIES                     :         15 records,      1 unique values
  FIRST AID KIT                                :         15 records,      1 unique values
  Telephone Hookup                             :         14 records,      2 unique values
  BOAT INCLUDED                                :         14 records,      1 unique values
  SAW                                          :         13 records,      1 unique values
  COMMUNITY PARK                               :         13 records,      1 unique values
  FITNESS TRAILS                               :         12 records,      1 unique values
  LOOKOUT TOWER                                :         11 records,      1 unique values
  ADIRONDACK SHELTER                           :         10 records,      1 unique values
  SNOW SHOVEL                                  :          9 records,      1 unique values
  CLOTHESLINE                                  :          9 records,      1 unique values
  BOAT MAINTENANCE                             :          9 records,      1 unique values
  PROPANE LANTERN (FUEL NOT PROVIDED)          :          8 records,      1 unique values
  FISH HATCHERY                                :          8 records,      1 unique values
  TWIN BED PLATFORM                            :          7 records,      1 unique values
  PROPANE GRILLS                               :          7 records,      1 unique values
  HAS RENTALS                                  :          7 records,      3 unique values
  ELECTRIC HOOKUPS 50 AMP                      :          6 records,      1 unique values
  COLEMAN STOVE (FUEL NOT PROVIDED)            :          6 records,      1 unique values
  BAY ACCESS                                   :          6 records,      1 unique values
  GROCERY STORE                                :          5 records,      1 unique values
  Clothes-Washer                               :          5 records,      1 unique values
  Clothes-Dryer                                :          5 records,      1 unique values
  Cabin Electricity                            :          5 records,      1 unique values
  Radio                                        :          4 records,      1 unique values
  PROPANE FIREPLACE                            :          4 records,      1 unique values
  OUTDOOR SHOWERS                              :          4 records,      1 unique values
  FISHING RENTALS                              :          4 records,      1 unique values
  FENCED PASTURES                              :          4 records,      1 unique values
  BATTERY LIGHTS                               :          4 records,      1 unique values
  Telephone                                    :          3 records,      1 unique values
  PROPANE LANTERN                              :          3 records,      1 unique values
  Maximum Group Capacity                       :          3 records,      3 unique values
  MULTI-USE COURT                              :          3 records,      1 unique values
  BUTTERFLY GARDEN                             :          3 records,      1 unique values
  AMPHITHEATHER                                :          3 records,      1 unique values
  SMALL REFRIDGERATOR                          :          2 records,      1 unique values
  OFF-ROAD VEHICLE RENTALS                     :          2 records,      1 unique values
  Dish-Washer                                  :          2 records,      1 unique values
  Television                                   :          1 records,      1 unique values
  SHOOTING RANGE                               :          1 records,      1 unique values
  RV SUPPLIES                                  :          1 records,      1 unique values
  RAIN CATCHMENT BARREL                        :          1 records,      1 unique values
  MEAT SHED                                    :          1 records,      1 unique values
  LIGHTHOUSE                                   :          1 records,      1 unique values
  FIRST AID STATION                            :          1 records,      1 unique values
  DVD                                          :          1 records,      1 unique values
  COLEMAN LANTERN (FUEL NOT PROVIDED)          :          1 records,      1 unique values
  CASINO                                       :          1 records,      1 unique values
  BUS STOP                                     :          1 records,      1 unique values
  BOAT TRIPS                                   :          1 records,      1 unique values
  ANCHORAGE                                    :          1 records,      1 unique values

  --- Driveway Entry (102,366 records, 12 unique values) ---
    'Back-In'                               :   58,762 ( 57.4%)
    'Back-in'                               :   27,499 ( 26.9%)
    'Pull-Through'                          :    7,299 (  7.1%)
    'Pull-through'                          :    5,225 (  5.1%)
    'Parallel'                              :    2,364 (  2.3%)
    'N/A'                                   :    1,056 (  1.0%)
    ''                                      :       79 (  0.1%)
    'Pull-Through '                         :       31 (  0.0%)
    'Back In'                               :       31 (  0.0%)
    'Pull-Thru'                             :       17 (  0.0%)
    'BACK-IN'                               :        2 (  0.0%)
    'pull-through'                          :        1 (  0.0%)

  --- Driveway Surface (105,454 records, 13 unique values) ---
    'Paved'                                 :   53,980 ( 51.2%)
    'Gravel'                                :   49,546 ( 47.0%)
    'N/A'                                   :    1,696 (  1.6%)
    'Grass'                                 :       84 (  0.1%)
    'GRAVEL'                                :       56 (  0.1%)
    'Gravel '                               :       36 (  0.0%)
    ''                                      :       25 (  0.0%)
    'gravel'                                :       15 (  0.0%)
    'PAVED'                                 :        9 (  0.0%)
    'Pull-through'                          :        3 (  0.0%)
    'Back-in'                               :        2 (  0.0%)
    'paved'                                 :        1 (  0.0%)
    'Slight'                                :        1 (  0.0%)

  --- Driveway Length (55,031 records, 564 unique values) ---
    '40'                                    :    4,029 (  7.3%)
    '30'                                    :    3,304 (  6.0%)
    '50'                                    :    3,136 (  5.7%)
    '0'                                     :    2,874 (  5.2%)
    '60'                                    :    2,523 (  4.6%)
    '45'                                    :    2,305 (  4.2%)
    '35'                                    :    2,215 (  4.0%)
    '20'                                    :    2,101 (  3.8%)
    '25'                                    :    1,794 (  3.3%)
    '55'                                    :    1,107 (  2.0%)
    '42'                                    :    1,051 (  1.9%)
    '36'                                    :    1,044 (  1.9%)
    '38'                                    :      891 (  1.6%)
    '32'                                    :      875 (  1.6%)
    '48'                                    :      855 (  1.6%)
    '70'                                    :      826 (  1.5%)
    '24'                                    :      798 (  1.5%)
    '28'                                    :      771 (  1.4%)
    '65'                                    :      742 (  1.3%)
    '46'                                    :      699 (  1.3%)
    '75'                                    :      669 (  1.2%)
    '22'                                    :      646 (  1.2%)
    '52'                                    :      640 (  1.2%)
    '18'                                    :      631 (  1.1%)
    '34'                                    :      587 (  1.1%)
    ... and 539 more values

  --- Driveway Grade (26,395 records, 8 unique values) ---
    'Slight'                                :   18,731 ( 71.0%)
    'Moderate'                              :    4,431 ( 16.8%)
    'N/A'                                   :    1,845 (  7.0%)
    'Severe'                                :    1,077 (  4.1%)
    ''                                      :      303 (  1.1%)
    'Gravel'                                :        4 (  0.0%)
    'Pull-through'                          :        2 (  0.0%)
    'Paved'                                 :        2 (  0.0%)

  --- Max Vehicle Length (103,209 records, 313 unique values) ---
    '40'                                    :    9,245 (  9.0%)
    '0'                                     :    8,948 (  8.7%)
    '30'                                    :    8,170 (  7.9%)
    '35'                                    :    6,211 (  6.0%)
    '20'                                    :    5,842 (  5.7%)
    '45'                                    :    5,449 (  5.3%)
    '50'                                    :    4,513 (  4.4%)
    '25'                                    :    4,290 (  4.2%)
    '60'                                    :    4,178 (  4.0%)
    '32'                                    :    2,148 (  2.1%)
    '55'                                    :    2,085 (  2.0%)
    ''                                      :    1,944 (  1.9%)
    '36'                                    :    1,913 (  1.9%)
    '18'                                    :    1,876 (  1.8%)
    '24'                                    :    1,851 (  1.8%)
    '38'                                    :    1,403 (  1.4%)
    '65'                                    :    1,221 (  1.2%)
    '28'                                    :    1,177 (  1.1%)
    '26'                                    :    1,173 (  1.1%)
    '42'                                    :    1,159 (  1.1%)
    '70'                                    :    1,130 (  1.1%)
    '15'                                    :    1,042 (  1.0%)
    '48'                                    :    1,005 (  1.0%)
    '22'                                    :    1,004 (  1.0%)
    '27'                                    :      823 (  0.8%)
    ... and 288 more values

  --- Site Access (49,827 records, 14 unique values) ---
    'Drive-In'                              :   36,046 ( 72.3%)
    'Drive In'                              :    8,009 ( 16.1%)
    'Hike-In'                               :    2,750 (  5.5%)
    'N/A'                                   :      834 (  1.7%)
    'Hike In'                               :      543 (  1.1%)
    'Boat-In'                               :      529 (  1.1%)
    'Walk-In'                               :      450 (  0.9%)
    ''                                      :      369 (  0.7%)
    'Boat In'                               :      268 (  0.5%)
    'Hike-In,Boat-In'                       :       13 (  0.0%)
    'Hike-In,Drive-In'                      :       10 (  0.0%)
    'Bike'                                  :        3 (  0.0%)
    'Drive in'                              :        2 (  0.0%)
    'Drive-Up'                              :        1 (  0.0%)

  --- Water Hookup (45,618 records, 7 unique values) ---
    'Yes'                                   :   26,490 ( 58.1%)
    'No'                                    :   18,262 ( 40.0%)
    'Y'                                     :      499 (  1.1%)
    ''                                      :      323 (  0.7%)
    'Water Hookup'                          :       36 (  0.1%)
    'NO'                                    :        6 (  0.0%)
    'yes'                                   :        2 (  0.0%)

  --- Sewer Hookup (10,274 records, 4 unique values) ---
    'No'                                    :    5,763 ( 56.1%)
    'Y'                                     :    3,026 ( 29.5%)
    'Yes'                                   :      817 (  8.0%)
    'Sewer Hookup'                          :      668 (  6.5%)

  --- Electricity Hookup (44,424 records, 57 unique values) ---
    '50'                                    :   20,042 ( 45.1%)
    '30'                                    :   12,745 ( 28.7%)
    'N/A'                                   :    4,622 ( 10.4%)
    '20/30/50'                              :    1,718 (  3.9%)
    '30/50'                                 :      947 (  2.1%)
    ''                                      :      770 (  1.7%)
    '15'                                    :      672 (  1.5%)
    '50/30'                                 :      526 (  1.2%)
    '20/30'                                 :      387 (  0.9%)
    '50 /20/30/50'                          :      360 (  0.8%)
    '50/30/20'                              :      358 (  0.8%)
    '20'                                    :      316 (  0.7%)
    '15/30/50'                              :      160 (  0.4%)
    '30 /50'                                :      145 (  0.3%)
    '50 /20/30'                             :       95 (  0.2%)
    '30/20'                                 :       73 (  0.2%)
    '50 /30/50'                             :       53 (  0.1%)
    '30 /30'                                :       47 (  0.1%)
    '20 /20'                                :       38 (  0.1%)
    '15/20/30'                              :       38 (  0.1%)
    'No'                                    :       35 (  0.1%)
    'Electricity Hookup'                    :       30 (  0.1%)
    '50 /50'                                :       26 (  0.1%)
    '50 /50/30/20'                          :       25 (  0.1%)
    '50 /30'                                :       21 (  0.0%)
    ... and 32 more values

  --- Full Hookup (1,778 records, 5 unique values) ---
    '50'                                    :    1,447 ( 81.4%)
    '30'                                    :      257 ( 14.5%)
    '15'                                    :       58 (  3.3%)
    '100'                                   :        9 (  0.5%)
    'Full Hookup'                           :        7 (  0.4%)

  --- Double Driveway (7,919 records, 6 unique values) ---
    'Y'                                     :    4,502 ( 56.9%)
    'Yes'                                   :    1,890 ( 23.9%)
    'No'                                    :      931 ( 11.8%)
    ''                                      :      428 (  5.4%)
    'yes'                                   :      135 (  1.7%)
    'YES'                                   :       33 (  0.4%)

  --- Capacity/Size Rating (105,323 records, 12 unique values) ---
    'Single'                                :   99,423 ( 94.4%)
    'Double'                                :    3,690 (  3.5%)
    'Group'                                 :      969 (  0.9%)
    'N/A'                                   :      534 (  0.5%)
    'Quad'                                  :      199 (  0.2%)
    'Triple'                                :      171 (  0.2%)
    'SINGLE'                                :      143 (  0.1%)
    ''                                      :      132 (  0.1%)
    'DOUBLE'                                :       32 (  0.0%)
    'Single '                               :       15 (  0.0%)
    'single'                                :        9 (  0.0%)
    'double'                                :        6 (  0.0%)

  --- Shade (89,341 records, 9 unique values) ---
    'Yes'                                   :   62,154 ( 69.6%)
    'Full'                                  :   23,456 ( 26.3%)
    'No'                                    :    2,945 (  3.3%)
    ''                                      :      438 (  0.5%)
    'Shade '                                :      205 (  0.2%)
    'yes'                                   :      127 (  0.1%)
    'no'                                    :       11 (  0.0%)
    'NO'                                    :        3 (  0.0%)
    'Partial'                               :        2 (  0.0%)

  --- Proximity to Water (18,396 records, 10 unique values) ---
    'Lakefront'                             :    8,767 ( 47.7%)
    'Riverfront'                            :    4,699 ( 25.5%)
    'N/A'                                   :    3,169 ( 17.2%)
    ''                                      :      683 (  3.7%)
    'Island'                                :      414 (  2.3%)
    'Oceanfront'                            :      290 (  1.6%)
    'Springs'                               :      273 (  1.5%)
    'Island,'                               :       75 (  0.4%)
    'Lakefront,Riverfront'                  :       19 (  0.1%)
    'Riverfront,Springs'                    :        7 (  0.0%)

  --- Shower/Bath Type (3,919 records, 5 unique values) ---
    'N/A'                                   :    1,626 ( 41.5%)
    'Shower Stall'                          :    1,463 ( 37.3%)
    ''                                      :      723 ( 18.4%)
    'Bathtub with Shower'                   :      101 (  2.6%)
    'Bathtub Only'                          :        6 (  0.2%)

  --- Accessibility (7,052 records, 2 unique values) ---
    'Y'                                     :    6,929 ( 98.3%)
    'Accessibility'                         :      123 (  1.7%)

  --- IS EQUIPMENT MANDATORY (110,562 records, 3 unique values) ---
    'true'                                  :   90,404 ( 81.8%)
    ''                                      :   15,449 ( 14.0%)
    'false'                                 :    4,709 (  4.3%)

  --- Campfire Allowed (95,200 records, 4 unique values) ---
    'Yes'                                   :   92,881 ( 97.6%)
    'No'                                    :    2,128 (  2.2%)
    'yes'                                   :      109 (  0.1%)
    ''                                      :       82 (  0.1%)

  --- Pets Allowed (113,295 records, 8 unique values) ---
    'Yes'                                   :  110,982 ( 98.0%)
    'No'                                    :    1,043 (  0.9%)
    'Pets Allowed'                          :      503 (  0.4%)
    'Domestic,Horse'                        :      344 (  0.3%)
    ''                                      :      189 (  0.2%)
    'yes'                                   :      170 (  0.2%)
    'Horse'                                 :       51 (  0.0%)
    'YES'                                   :       13 (  0.0%)

  --- Site Rating (27,497 records, 10 unique values) ---
    'Standard'                              :   16,198 ( 58.9%)
    'Prime'                                 :    3,911 ( 14.2%)
    'Basic'                                 :    3,161 ( 11.5%)
    'Preferred'                             :    2,012 (  7.3%)
    'N/A'                                   :    1,564 (  5.7%)
    ''                                      :      623 (  2.3%)
    'Good'                                  :       23 (  0.1%)
    'Standar'                               :        3 (  0.0%)
    'PRIME'                                 :        1 (  0.0%)
    'PREFER'                                :        1 (  0.0%)

  --- Condition Rating (23,834 records, 11 unique values) ---
    'Good'                                  :   10,800 ( 45.3%)
    'Basic'                                 :    3,447 ( 14.5%)
    'Standard'                              :    3,379 ( 14.2%)
    'Prime'                                 :    3,047 ( 12.8%)
    'N/A'                                   :    1,807 (  7.6%)
    ''                                      :      673 (  2.8%)
    'Preferred'                             :      472 (  2.0%)
    'Poor'                                  :      206 (  0.9%)
    'PRIME'                                 :        1 (  0.0%)
    'PREFER'                                :        1 (  0.0%)
    'BASIC'                                 :        1 (  0.0%)

  --- Location Rating (25,446 records, 9 unique values) ---
    'Good'                                  :   16,080 ( 63.2%)
    'Prime'                                 :    6,648 ( 26.1%)
    'N/A'                                   :    1,808 (  7.1%)
    ''                                      :      668 (  2.6%)
    'Poor'                                  :      195 (  0.8%)
    'GOOD'                                  :       26 (  0.1%)
    'good'                                  :       12 (  0.0%)
    'PRIME'                                 :        6 (  0.0%)
    'POOR'                                  :        3 (  0.0%)

  --- Checkout Time (123,255 records, 83 unique values) ---
    '12:00 PM'                              :   49,665 ( 40.3%)
    '11:00 AM'                              :   16,386 ( 13.3%)
    '2:00 PM'                               :   11,139 (  9.0%)
    '1:00 PM'                               :    9,437 (  7.7%)
    '4:00 PM'                               :    8,254 (  6.7%)
    '3:00 PM'                               :    7,062 (  5.7%)
    '02:00 PM'                              :    2,922 (  2.4%)
    '0:00 AM'                               :    2,448 (  2.0%)
    '10:00 AM'                              :    2,152 (  1.7%)
    '6:00 PM'                               :    1,994 (  1.6%)
    '04:00 PM'                              :    1,867 (  1.5%)
    '03:00 PM'                              :    1,364 (  1.1%)
    '01:00 PM'                              :    1,196 (  1.0%)
    '10:00 PM'                              :    1,021 (  0.8%)
    '5:00 PM'                               :      999 (  0.8%)
    '4:30 PM'                               :      968 (  0.8%)
    ''                                      :      851 (  0.7%)
    '05:00 PM'                              :      517 (  0.4%)
    '11:30 AM'                              :      387 (  0.3%)
    '9:00 PM'                               :      269 (  0.2%)
    '06:00 PM'                              :      268 (  0.2%)
    '1:30 PM'                               :      238 (  0.2%)
    '8:00 PM'                               :      232 (  0.2%)
    '2:30 PM'                               :      216 (  0.2%)
    '0:00 PM'                               :      174 (  0.1%)
    ... and 58 more values

  --- Checkin Time (123,093 records, 84 unique values) ---
    '2:00 PM'                               :   40,439 ( 32.9%)
    '3:00 PM'                               :   16,778 ( 13.6%)
    '12:00 PM'                              :   10,778 (  8.8%)
    '4:00 PM'                               :    9,175 (  7.5%)
    '1:00 PM'                               :    8,471 (  6.9%)
    '02:00 PM'                              :    7,538 (  6.1%)
    '6:00 PM'                               :    6,875 (  5.6%)
    '5:00 PM'                               :    5,281 (  4.3%)
    '03:00 PM'                              :    2,649 (  2.2%)
    '0:00 AM'                               :    2,413 (  2.0%)
    '04:00 PM'                              :    2,273 (  1.8%)
    '01:00 PM'                              :    1,544 (  1.3%)
    '06:00 PM'                              :    1,459 (  1.2%)
    '05:00 PM'                              :    1,139 (  0.9%)
    ''                                      :      693 (  0.6%)
    '10:00 AM'                              :      677 (  0.5%)
    '8:00 AM'                               :      533 (  0.4%)
    '6:00 AM'                               :      466 (  0.4%)
    '12:30 PM'                              :      452 (  0.4%)
    '11:00 AM'                              :      427 (  0.3%)
    '06:00 AM'                              :      415 (  0.3%)
    '2:30 PM'                               :      375 (  0.3%)
    '12:01 PM'                              :      258 (  0.2%)
    '3:30 PM'                               :      216 (  0.2%)
    '08:00 AM'                              :      211 (  0.2%)
    ... and 59 more values

================================================================================
  7. CAMPSITE EQUIPMENT - Complete inventory
================================================================================
Total equipment records: 431,992
Unique equipment names: 15

All equipment types:
  Tent                          :  102,753 records | len: 1-500ft (avg 44) | zero_len: 44,106
  RV                            :   87,950 records | len: 1-500ft (avg 43) | zero_len: 15,500
  Trailer                       :   85,285 records | len: 1-500ft (avg 43) | zero_len: 16,354
  PICKUP CAMPER                 :   24,429 records | len: 1-120ft (avg 31) | zero_len: 16,457
  POP UP                        :   21,832 records | len: 8-255ft (avg 32) | zero_len: 14,711
  CARAVAN/CAMPER VAN            :   19,691 records | len: 10-120ft (avg 32) | zero_len: 11,077
  FIFTH WHEEL                   :   18,595 records | len: 6-350ft (avg 37) | zero_len: 10,299
  SMALL TENT                    :   17,828 records | len: 5-70ft (avg 23) | zero_len: 17,239
  VEHICLE                       :   16,807 records | len: 8-100ft (avg 31) | zero_len: 11,249
  CAR                           :   13,403 records | len: 10-120ft (avg 31) | zero_len: 9,653
  LARGE TENT OVER 9X12`         :   13,353 records | len: 10-72ft (avg 29) | zero_len: 12,800
  Boat                          :    4,538 records | len: 8-85ft (avg 34) | zero_len: 3,311
  Hammock                       :    2,197 records | len: 12-64ft (avg 37) | zero_len: 2,113
  RV/MOTORHOME                  :    1,943 records | len: 16-65ft (avg 36) | zero_len: 1,312
  Horse                         :    1,388 records | len: 1-115ft (avg 42) | zero_len: 568

RV max_length distribution:
  0 (zero/unknown)         :   15,500
  1-15 ft                  :      393
  16-20 ft                 :    3,508
  21-25 ft                 :    5,971
  26-30 ft                 :    9,949
  31-35 ft                 :    8,631
  36-40 ft                 :   12,075
  41-45 ft                 :    7,547
  46-60 ft                 :   15,338
  60+ ft                   :    9,038

================================================================================
  8. ORGANIZATIONS - Deep look
================================================================================
All organizations with facility and campsite stats:
  FS       USDA Forest Service                          
         type=Federal Agency  facs=9,602 campgr=3,636 generic=5,628 resv=3,539 coords=7,399 desc=9,290
  USACE    US Army Corps of Engineers                   
         type=Federal Agency  facs=2,108 campgr=1,046 generic=  784 resv=1,272 coords=1,903 desc=1,835
  NPS      National Park Service                        
         type=Federal Agency  facs=1,626 campgr=  600 generic=  566 resv=  626 coords=1,533 desc=1,532
  BLM      Bureau of Land Management                    
         type=Federal Agency  facs=1,249 campgr=  314 generic=  841 resv=  242 coords=1,213 desc=1,176
  FWS      Fish and Wildlife Service                    
         type=Federal Agency  facs=  162 campgr=    7 generic=  133 resv=   26 coords=  152 desc=  149
  SIAP     Smithsonian Institution Affiliations Program 
         type=Federal Agency  facs=  105 campgr=    0 generic=  105 resv=    0 coords=   77 desc=  105
  NRHP     National Register of Historic Places         
         type=Federal Agency  facs=   57 campgr=    0 generic=   57 resv=    0 coords=   57 desc=   57
  ABMC     American Battle Monuments Commission         
         type=Federal Agency  facs=   24 campgr=    0 generic=    0 resv=    0 coords=   24 desc=   24
  BOR      Bureau of Reclamation                        
         type=Federal Agency  facs=   18 campgr=   14 generic=    0 resv=   17 coords=   17 desc=   15
  SI       Smithsonian Institution                      
         type=Federal Agency  facs=   16 campgr=    0 generic=   14 resv=    0 coords=   16 desc=   16
  NARA     National Archives and Records Administration 
         type=Federal Agency  facs=   16 campgr=    0 generic=    2 resv=    1 coords=   16 desc=   16
           Historic Hotels of America                   
         type=Federal Agency  facs=   15 campgr=    0 generic=   15 resv=    0 coords=   15 desc=   15
  NHL      National Historic Landmark                   
         type=Federal Agency  facs=   13 campgr=    0 generic=   13 resv=    0 coords=   13 desc=   13
  NOAA     National Oceanic and Atmospheric Administration
         type=Federal Agency  facs=   10 campgr=    0 generic=   10 resv=    0 coords=   10 desc=   10
  FED      FEDERAL                                      
         type=Label           facs=    9 campgr=    8 generic=    1 resv=    8 coords=    8 desc=    1
  Presidio Presidio Trust                               
         type=Federal Agency  facs=    6 campgr=    1 generic=    0 resv=    6 coords=    6 desc=    1
  BEP      Bureau of Engraving and Printing             
         type=Federal Agency  facs=    2 campgr=    0 generic=    1 resv=    0 coords=    2 desc=    2
  NAVY     Commander, Navy Installation Command (CNIC)  
         type=Federal Agency  facs=    2 campgr=    2 generic=    0 resv=    2 coords=    2 desc=    2
  DOI      Department of the Interior                   
         type=Federal Department facs=    1 campgr=    0 generic=    1 resv=    0 coords=    1 desc=    1
  USAF     US Air Force                                 
         type=Federal Agency  facs=    1 campgr=    0 generic=    1 resv=    0 coords=    1 desc=    1
  MD       Maryland                                     
         type=State           facs=    1 campgr=    0 generic=    1 resv=    0 coords=    1 desc=    1
  TVA      Tennessee Valley Authority                   
         type=Federal Agency  facs=    0 campgr=    0 generic=    0 resv=    0 coords=    0 desc=    0
  DOT      Department of Transportation                 
         type=Federal Department facs=    0 campgr=    0 generic=    0 resv=    0 coords=    0 desc=    0
  DOC      Department of Commerce                       
         type=Federal Department facs=    0 campgr=    0 generic=    0 resv=    0 coords=    0 desc=    0
  DOD      Department of Defense                        
         type=Federal Department facs=    0 campgr=    0 generic=    0 resv=    0 coords=    0 desc=    0
  USDA     Department of Agriculture                    
         type=Federal Department facs=    0 campgr=    0 generic=    0 resv=    0 coords=    0 desc=    0
  Treasury Department of the Treasury                   
         type=Federal Department facs=    0 campgr=    0 generic=    0 resv=    0 coords=    0 desc=    0
  STATEPARKS STATE PARKS                                  
         type=Label           facs=    0 campgr=    0 generic=    0 resv=    0 coords=    0 desc=    0
  TX       Texas                                        
         type=State           facs=    0 campgr=    0 generic=    0 resv=    0 coords=    0 desc=    0
  UT       Utah                                         
         type=State           facs=    0 campgr=    0 generic=    0 resv=    0 coords=    0 desc=    0
  NM       New Mexico                                   
         type=State           facs=    0 campgr=    0 generic=    0 resv=    0 coords=    0 desc=    0
  USGS     United States Geological Survey              
         type=Federal Agency  facs=    0 campgr=    0 generic=    0 resv=    0 coords=    0 desc=    0
  VA       Virginia                                     
         type=State           facs=    0 campgr=    0 generic=    0 resv=    0 coords=    0 desc=    0

Campsites per organization:
  FS       USDA Forest Service                     : 3,203 facilities,   61,925 campsites
  USACE    US Army Corps of Engineers              :   994 facilities,   40,967 campsites
  NPS      National Park Service                   :   414 facilities,   21,307 campsites
  BLM      Bureau of Land Management               :   149 facilities,    3,100 campsites
  BOR      Bureau of Reclamation                   :    14 facilities,      721 campsites
  FWS      Fish and Wildlife Service               :     7 facilities,      166 campsites
  NAVY     Commander, Navy Installation Command (CNIC):     2 facilities,       16 campsites
  Presidio Presidio Trust                          :     1 facilities,        4 campsites

================================================================================
  9. REC AREAS <-> FACILITIES relationship
================================================================================
Total rec areas: 3,671
Facilities with parent rec area: 14,279
Facilities without: 782
Rec areas referenced by facilities: 1,104
Rec areas with no facilities linked: 2,567

Rec area coordinates:
  Valid: 3,191
  Zero: 480

Rec area description completeness:
  Has description: 3,653 / 3,671
  Has directions: 3,517 / 3,671

================================================================================
  10. LINKS - What URLs exist
================================================================================
Total links: 64,550

By link_type and entity_type:
  Official Web Site                   (Asset     ): 42,200
  Other                               (Asset     ): 11,777
  Map                                 (Asset     ):  4,790
  Reservation                         (Asset     ):  1,313
  Facebook                            (Asset     ):    851
  Concessionaire                      (Asset     ):    579
  1                                   (Asset     ):    554
  Twitter                             (Asset     ):    436
  Flickr                              (Asset     ):    413
  YouTube Channel                     (Asset     ):    317
  YouTube                             (Asset     ):    213
  Local Partnerships                  (Asset     ):    178
  3                                   (Asset     ):    172
  Google+                             (Asset     ):    123
  Facebook Page                       (Asset     ):     80
  Twitter Feed                        (Asset     ):     80
  Virtual Tour                        (Asset     ):     78
  Official Web Site                   (Tour      ):     71
  Flickr Album                        (Asset     ):     52
  2                                   (Asset     ):     51
  5                                   (Asset     ):     35
  4                                   (Asset     ):     28
  Concessionaires                     (Asset     ):     28
  10                                  (Asset     ):     27
  14                                  (Asset     ):     27
  15                                  (Asset     ):     24
  6                                   (Asset     ):     18
  7                                   (Asset     ):     16
  8                                   (Asset     ):     16
  17                                  (Asset     ):      1
  18                                  (Asset     ):      1
  20                                  (Asset     ):      1

Facility link coverage:
  Facilities with links: 0 / 15,061

Top URL domains in links:
  fs.usda.gov              : 31,087
  other                    : 20,552
  nps.gov                  :  6,454
  recreation.gov           :  1,937
  facebook.com             :  1,072
  blm.gov                  :    833
  twitter/x.com            :    728
  youtube.com              :    727
  fws.gov                  :    646
  usace.army.mil           :    246
  google.com               :    136
  usbr.gov                 :     67
  instagram.com            :      9

================================================================================
  11. FACILITY ACTIVITIES - What activities exist
================================================================================
Total activity assignments: 48,795
Unique activities: 151
Facilities with activities: 10,714

All activities:
  HIKING                                       :  6,335 assignments (6,335 facilities)
  CAMPING                                      :  5,546 assignments (5,546 facilities)
  FISHING                                      :  4,640 assignments (4,640 facilities)
  BOATING                                      :  3,011 assignments (3,011 facilities)
  WILDLIFE VIEWING                             :  2,760 assignments (2,760 facilities)
  PICNICKING                                   :  2,728 assignments (2,728 facilities)
  BIKING                                       :  2,608 assignments (2,608 facilities)
  HORSEBACK RIDING                             :  2,041 assignments (2,041 facilities)
  HUNTING                                      :  1,374 assignments (1,374 facilities)
  WATER SPORTS                                 :  1,182 assignments (1,182 facilities)
  PHOTOGRAPHY                                  :    907 assignments (  907 facilities)
  SWIMMING                                     :    893 assignments (  893 facilities)
  SWIMMING SITE                                :    864 assignments (  864 facilities)
  DAY USE AREA                                 :    862 assignments (  862 facilities)
  OFF HIGHWAY VEHICLE                          :    693 assignments (  693 facilities)
  BIRDING                                      :    663 assignments (  663 facilities)
  VISITOR CENTER                               :    622 assignments (  622 facilities)
  HISTORIC & CULTURAL SITE                     :    621 assignments (  621 facilities)
  INTERPRETIVE PROGRAMS                        :    588 assignments (  588 facilities)
  AUTO TOURING                                 :    558 assignments (  558 facilities)
  WATER ACCESS                                 :    544 assignments (  544 facilities)
  RECREATIONAL VEHICLES                        :    537 assignments (  537 facilities)
  CANOEING                                     :    490 assignments (  490 facilities)
  KAYAKING                                     :    460 assignments (  460 facilities)
  MOUNTAIN BIKING                              :    436 assignments (  436 facilities)
  WINTER SPORTS                                :    418 assignments (  418 facilities)
  PLAYGROUND PARK SPECIALIZED SPORT SITE       :    397 assignments (  397 facilities)
  HORSE CAMPING                                :    394 assignments (  394 facilities)
  HOTEL/LODGE/RESORT PRIVATELY OWNED           :    347 assignments (  347 facilities)
  OTHER RECREATION CONCESSION SITE             :    307 assignments (  307 facilities)
  SCENIC DRIVE                                 :    303 assignments (  303 facilities)
  STAR GAZING                                  :    290 assignments (  290 facilities)
  BACKPACKING                                  :    288 assignments (  288 facilities)
  WILDERNESS                                   :    248 assignments (  248 facilities)
  FIRE LOOKOUTS/CABINS OVERNIGHT               :    227 assignments (  227 facilities)
  PADDLING                                     :    222 assignments (  222 facilities)
  WATER ACTIVITIES                             :    219 assignments (  219 facilities)
  CLIMBING                                     :    191 assignments (  191 facilities)
  NON-MOTORIZED BOATING                        :    148 assignments (  148 facilities)
  OFF ROAD VEHICLE TRAILS                      :    127 assignments (  127 facilities)
  ENVIRONMENTAL EDUCATION                      :    111 assignments (  111 facilities)
  BERRY PICKING                                :    108 assignments (  108 facilities)
  OFF HIGHWAY VEHICLE TRAILS                   :    107 assignments (  107 facilities)
  FISH HATCHERY                                :     99 assignments (   99 facilities)
  MOTOR BOAT                                   :     94 assignments (   94 facilities)
  PADDLE BOATING                               :     91 assignments (   91 facilities)
  AMPHITHEATER                                 :     91 assignments (   91 facilities)
  RANGER STATION                               :     83 assignments (   83 facilities)
  HISTORIC SITES                               :     78 assignments (   78 facilities)
  INFORMATION SITE                             :     76 assignments (   76 facilities)
  WATER SKIING                                 :     75 assignments (   75 facilities)
  ROCK CLIMBING                                :     73 assignments (   73 facilities)
  TUBING                                       :     70 assignments (   70 facilities)
  RAFTING                                      :     70 assignments (   70 facilities)
  EVENING PROGRAMS                             :     69 assignments (   69 facilities)
  CROSS COUNTRY SKIING                         :     69 assignments (   69 facilities)
  JET SKIING                                   :     67 assignments (   67 facilities)
  SNOWSHOEING                                  :     60 assignments (   60 facilities)
  ACCESSIBLE SWIMMING                          :     60 assignments (   60 facilities)
  MUSHROOM PICKING                             :     55 assignments (   55 facilities)
  SAILING                                      :     54 assignments (   54 facilities)
  DISC GOLF                                    :     52 assignments (   52 facilities)
  CULTURAL ACTIVITIES                          :     50 assignments (   50 facilities)
  GUIDED INTERPRETIVE WALKS                    :     46 assignments (   46 facilities)
  WHITEWATER RAFTING                           :     43 assignments (   43 facilities)
  BEACHCOMBING                                 :     40 assignments (   40 facilities)
  OBSERVATION SITE                             :     36 assignments (   36 facilities)
  MOUNTAIN CLIMBING                            :     36 assignments (   36 facilities)
  FISH VIEWING SITE                            :     33 assignments (   33 facilities)
  Camping Area                                 :     32 assignments (   32 facilities)
  Accessible Facility or Activity              :     32 assignments (   32 facilities)
  ICE FISHING                                  :     30 assignments (   30 facilities)
  SKIING                                       :     29 assignments (   29 facilities)
  EDUCATIONAL PROGRAMS                         :     28 assignments (   28 facilities)
  SNOWMOBILE                                   :     26 assignments (   26 facilities)
  RIVER TRIPS                                  :     26 assignments (   26 facilities)
  SNOWMOBILE TRAILS                            :     24 assignments (   24 facilities)
  MUSEUM                                       :     23 assignments (   23 facilities)
  Dispersed Camping                            :     21 assignments (   21 facilities)
  DIVING                                       :     21 assignments (   21 facilities)
  SNORKELING                                   :     19 assignments (   19 facilities)
  RECREATION PROGRAMS                          :     18 assignments (   18 facilities)
  BIRD WATCHING                                :     18 assignments (   18 facilities)
  SEA KAYAKING                                 :     17 assignments (   17 facilities)
  SCUBA DIVING                                 :     17 assignments (   17 facilities)
  GOLD PANNING                                 :     17 assignments (   17 facilities)
  WOOD CUTTING                                 :     16 assignments (   16 facilities)
  HOTEL/LODGE/RESORT FS OWNED                  :     15 assignments (   15 facilities)
  CRAWFISHING                                  :     14 assignments (   14 facilities)
  SLEDDING                                     :     13 assignments (   13 facilities)
  LOOKOUT TOWER                                :     13 assignments (   13 facilities)
  CAVING                                       :     13 assignments (   13 facilities)
  Trail Running                                :     12 assignments (   12 facilities)
  STARGAZING                                   :     12 assignments (   12 facilities)
  SOFTBALL FIELDS                              :     12 assignments (   12 facilities)
  ARCHERY                                      :     11 assignments (   11 facilities)
  SAILBOARDING                                 :     10 assignments (   10 facilities)
  WHALE WATCHING                               :      9 assignments (    9 facilities)
  Dogs on Leash (Leash Required)               :      9 assignments (    9 facilities)
  WILD HORSE VIEWING                           :      8 assignments (    8 facilities)
  RECREATIONAL SHOOTING                        :      8 assignments (    8 facilities)
  ICE CLIMBING                                 :      8 assignments (    8 facilities)
  CRABBING                                     :      8 assignments (    8 facilities)
  WINDSURFING                                  :      7 assignments (    7 facilities)
  SURFING                                      :      7 assignments (    7 facilities)
  WINERY TOURS                                 :      6 assignments (    6 facilities)
  PICNIC TABLES                                :      6 assignments (    6 facilities)
  HIKING TRAIL                                 :      6 assignments (    6 facilities)
  GOLF                                         :      6 assignments (    6 facilities)
  BEACH CAMPING                                :      6 assignments (    6 facilities)
  SOCCER FIELDS                                :      4 assignments (    4 facilities)
  SNOWMOBILING                                 :      4 assignments (    4 facilities)
  Rockhounding                                 :      4 assignments (    4 facilities)
  CLAM DIGGING                                 :      4 assignments (    4 facilities)
  ANTIQUING                                    :      4 assignments (    4 facilities)
  TRAILS, HORSE                                :      3 assignments (    3 facilities)
  SNOWBOARDING                                 :      3 assignments (    3 facilities)
  DOWNHILL SKIING                              :      3 assignments (    3 facilities)
  BADMINTON                                    :      3 assignments (    3 facilities)
  Skijoring                                    :      2 assignments (    2 facilities)
  Skate Skiing                                 :      2 assignments (    2 facilities)
  Shooting Range                               :      2 assignments (    2 facilities)
  SNOW TUBING                                  :      2 assignments (    2 facilities)
  ORGANIZATION SITE FS OWNED                   :      2 assignments (    2 facilities)
  MOTEL                                        :      2 assignments (    2 facilities)
  MARINA                                       :      2 assignments (    2 facilities)
  Hot Springs Soaking                          :      2 assignments (    2 facilities)
  Hang Gliding - Parasailing                   :      2 assignments (    2 facilities)
  Fly Fishing                                  :      2 assignments (    2 facilities)
  EMERGENCY SERVICES                           :      2 assignments (    2 facilities)
  E-Biking, Class 1                            :      2 assignments (    2 facilities)
  BOAT RENTAL                                  :      2 assignments (    2 facilities)
  Trapping                                     :      1 assignments (    1 facilities)
  TRAILS, DIFFICULT HIKING                     :      1 assignments (    1 facilities)
  TRAILS, ALL TERRAIN/OHV                      :      1 assignments (    1 facilities)
  Snow Fat Tire Biking                         :      1 assignments (    1 facilities)
  Scuba Diving                                 :      1 assignments (    1 facilities)
  SHUFFLE BOARD                                :      1 assignments (    1 facilities)
  RECREATION RESIDENCE                         :      1 assignments (    1 facilities)
  OHV Use - Ultralight                         :      1 assignments (    1 facilities)
  Long Term Visitor Area                       :      1 assignments (    1 facilities)
  Land - Sand Sailing                          :      1 assignments (    1 facilities)
  ICE SKATING                                  :      1 assignments (    1 facilities)
  Geocaching                                   :      1 assignments (    1 facilities)
  GONDOLA RIDES                                :      1 assignments (    1 facilities)
  Fat Tire Biking                              :      1 assignments (    1 facilities)
  E-Biking, Class 3                            :      1 assignments (    1 facilities)
  E-Biking, Class 2                            :      1 assignments (    1 facilities)
  Dog Mushing                                  :      1 assignments (    1 facilities)
  Canyoneering                                 :      1 assignments (    1 facilities)
  Bouldering                                   :      1 assignments (    1 facilities)

================================================================================
  12. CROSS-REFERENCE: Campsite type vs attributes present
================================================================================
Which campsite types have which attributes (% of sites with that attribute):
Type                           Driveway Driveway Max Vehi Water Ho Sewer Ho Electric Pets All Campfire Site Acc
---------------------------------------------------------------------------------------------------------------
STANDARD NONELECTRIC                83%      82%      80%      21%       7%       5%      87%      74%      43%
STANDARD ELECTRIC                   97%      97%      96%      70%      12%      99%      96%      79%      23%
RV NONELECTRIC                      79%      78%      80%      22%       4%       5%      84%      79%      59%
RV ELECTRIC                         83%      84%      68%      81%      35%      96%      95%      84%      50%
TENT ONLY NONELECTRIC               57%      70%      65%      18%       4%       8%      90%      77%      53%
MANAGEMENT                          44%      45%      44%      17%       4%      15%      49%      42%      21%
CABIN NONELECTRIC                   20%      50%      68%      23%       2%      11%      52%      48%      34%
CABIN ELECTRIC                      41%      64%      51%      20%       3%      25%      65%      66%      70%
WALK TO                             34%      57%      64%      22%       6%      12%      89%      74%      52%
BOAT IN                              5%       6%      15%       9%       0%       1%      88%      70%      70%

================================================================================
  13. CROSS-REFERENCE: Campsite type vs equipment present
================================================================================
Which campsite types allow which equipment (% of sites):
Type                                 RV  Trailer FIFTH WH     Tent SMALL TE PICKUP C CARAVAN/     Boat
------------------------------------------------------------------------------------------------------
STANDARD NONELECTRIC                76%      72%      13%      83%      14%      21%      17%       3%
STANDARD ELECTRIC                   93%      95%      22%      95%      13%      23%      15%       4%
RV NONELECTRIC                      79%      67%      33%      33%      16%      45%      42%       5%
RV ELECTRIC                         86%      61%      42%      36%      13%      32%      32%       9%
TENT ONLY NONELECTRIC                1%       1%       0%      87%      20%       1%       1%       0%
MANAGEMENT                          36%      36%       6%      45%       8%       9%       8%       2%
CABIN NONELECTRIC                    2%       1%       0%       2%       1%       1%       5%       1%
CABIN ELECTRIC                       1%       1%       0%       2%       0%       1%       1%       0%
WALK TO                              0%       0%       0%      86%      17%       1%       1%       0%
BOAT IN                              0%       0%       0%      63%       9%       0%       0%      43%

================================================================================
  14. PERMIT ENTRANCES
================================================================================
Total: 857

By type:
  Entry Point                   :   183
  Trailhead                     :   112
  Small Campsite, 2 Tent Pads   :   104
  Campsite                      :    63
  Designated Campsite           :    46
  Non Zone South                :    32
  Backcountry Lakes             :    32
  Large Campsite, 4 Tent Pads   :    25
  Group Site                    :    21
  Zone                          :    20
  03 Mountain Camping Zones     :    20
  Ovrq                          :    19
  09 Other Climbing Sites       :    15
  Non Zone North                :    14
  Individual Campsite           :    14
  Boat Launch                   :    14
  Grassy Lake                   :    13
  01 Jackson Lake               :    13
  04 Mountain Group Sites       :    12
  02 Leigh Lake                 :    12
  Campground                    :    11
  Parking Space                 :    10
  Platform                      :     7
  River                         :     5
  Land with Platform            :     5
  River Segment                 :     4
  Cabin                         :     4
  05 Northern Canyons           :     4
  Wilderness                    :     3
  08 Lwr Saddle-Moraine-Caves   :     3
  Permit Area                   :     2
  John D. Rockefeller Parkway   :     2
  Houseboat                     :     2
  07 Meadows-Platforms          :     2
  Small Campsite, 0 Tent Pads   :     1
  Entry Point-Restricted        :     1
  Entry Point - Zone 5          :     1
  Entry Point - Zone 4          :     1
  Entry Point - Zone 3          :     1
  Entry Point - Zone 2          :     1
  Entry Point - Zone 1          :     1
  Accessible Sites              :     1
  06 South Fork - Garnet Canyon :     1

Facilities with permit entrances:
  47 facilities

Permit entrances by organization:
  NPS     :   492
  FS      :   328
  BLM     :    22
  FWS     :    12

================================================================================
  15. ADDRESSES - State coverage
================================================================================
Facility addresses:
  Total address records: 16,328
  Unique states: 79

All states/territories represented:
  CA   :  2,208
  UT   :  1,566
  CO   :  1,225
  WY   :  1,090
  OR   :  1,067
  ID   :    868
  MT   :    672
  WA   :    623
  AZ   :    617
  NM   :    458
  NC   :    458
  AK   :    402
  TX   :    386
  OK   :    303
  AR   :    286
  GA   :    240
  TN   :    235
  MI   :    216
  NV   :    202
  KY   :    199
  VA   :    195
  SD   :    175
  WV   :    157
  MO   :    152
  MS   :    151
  MN   :    151
  PA   :    133
  KS   :    121
  NY   :    113
  SC   :    107
  MD   :    106
  IA   :    104
  AL   :    103
  FL   :    101
  ME   :     97
  IL   :     93
  NH   :     92
  OH   :     83
  WI   :     71
  ND   :     70
  MA   :     69
  LA   :     68
  VT   :     63
  IN   :     46
  NE   :     42
  HI   :     38
  DC   :     36
  OREGON:     16
  NJ   :     11
  PR   :     10
  VI   :      9
  Tennessee:      8
  STATE MAPPING BROKEN:      8
  Oregon:      5
  California:      5
  CT   :      5
  RI   :      4
  AS   :      4
  Wyoming:      3
  Washington:      3
  MP   :      3
  Arizona:      3
  Virginia:      2
  UTAH :      2
  GU   :      2
  Colorado:      2
  Alaska:      2
  WASHINGTON:      1
  Utah :      1
  TEXAS:      1
  TENNESSEE:      1
  MONTANA:      1
  Idaho:      1
  IOWA :      1
  IN   :      1
  ILE-DE-FRANCE:      1
  FM   :      1
  DE   :      1
  ARIZONA:      1

Rec area addresses:
  Total: 3,878
  Unique states: 58

Facilities without any address record:
  1,804 facilities have no address

================================================================================
  16. DATA FRESHNESS - Last updated dates
================================================================================
Facility last_updated distribution:
  2020:  7,083
  2021:    630
  2022:    483
  2023:    383
  2024:    524
  2025:  1,848
  2026:  4,110

Campsite last_updated distribution:
  2018:      6
  2020:     74
  2021:     12
  2022:     84
  2023:      4
  2024:      2
  2025: 128,591
  2026:  4,201

Rec area last_updated distribution:
  2020:    725
  2021:    843
  2022:    536
  2023:    299
  2024:    267
  2025:    759
  2026:    242

Most recently updated facilities (top 10):
  2026-02-07                GUN CREEK
  2026-02-07                WHEATLAND PARK
  2026-02-07                BOLAN MOUNTAIN LOOKOUT
  2026-02-07                NORTH MARCUM DAY USE AREA
  2026-02-07                OUTLET PARK
  2026-02-07                SHAGBARK GROUP AREA
  2026-02-07                LIGHTFOOT LANDING
  2026-02-07                OUTLET(MELVERN)
  2026-02-07                NEMO LANDING
  2026-02-07                Hayden Flat Group Campground

Oldest last_updated facilities (top 10):
  2020-09-10                Six Mile Campground
  2020-09-10                Nelson Crag Trailhead
  2020-09-10                Wheeler Brook East Trailhead
  2020-09-10                Miles Notch Trailhead
  2020-09-10                West Mountain Snow-parking area
  2020-09-10                Beehive ORV Trailhead
  2020-09-10                Blue Springs Summit Sno-Park
  2020-09-10                River Bench Day Use
  2020-09-10                Rob Brook - Nana XC-Ski Trailhead
  2020-09-10                Heavens Gate Overlook

================================================================================
  17. EDGE CASES AND ANOMALIES
================================================================================
Orphaned campsites (facility_id not in facilities table):
  4,768

Non-Campground facilities that have campsites:
  Permit                        :     2 facilities,     34 campsites

MANAGEMENT campsites — deeper look:
  Total: 10,949
  Reservable: 72
  Top equipment: Tent(4,891), RV(3,969), Trailer(3,936), PICKUP CAMPER(1,007), CARAVAN/CAMPER VAN(906)

  MANAGEMENT campsites by org:
    FS      :  7,137
    USACE   :  1,720
    NPS     :  1,316
    BLM     :    189
    FWS     :     10
    BOR     :      6

Most common facility names (possible duplicates):
  Visitor Center                               :  43 occurrences
                                               :   8 occurrences
  Wilderness areas                             :   5 occurrences
  North Fork Campground                        :   5 occurrences
  State Park                                   :   4 occurrences
  Spring Creek Campground                      :   4 occurrences
  Deer Creek Trailhead                         :   4 occurrences
  Black Bear Management Program                :   4 occurrences

Campsites with potentially bad non-zero coords:
  Out of range: 0

Most-shared facility coordinates (potential data entry errors):
  (46.962405, -90.660457):   14 facilities share this exact point

Facility descriptions mentioning RV-related terms:
  'RV':  7,175 facilities
  'motorhome':     42 facilities
  'fifth wheel':     14 facilities
  'hookup':  1,029 facilities
  'dump station':    678 facilities
  'pull-through':    103 facilities
  'pull through':     25 facilities
  'full hook':     55 facilities
  'electric hook':    493 facilities
  'water hook':    250 facilities
  'sewer hook':     45 facilities
  '30 amp':     34 facilities
  '50 amp':     64 facilities
  'generator':     59 facilities
  'not recommended for rv':      4 facilities
  'no rv':     46 facilities
  'gravel road':    126 facilities
  'dirt road':    127 facilities
  'paved road':    190 facilities
  'high clearance':    114 facilities
  '4wd':     77 facilities
  'four wheel':     19 facilities
  'dispersed':    342 facilities
  'primitive':    731 facilities
  'dry camp':     16 facilities
  'vault toilet':  2,414 facilities
  'potable water':    580 facilities

Campsites typed 'TENT ONLY' but with RV equipment:
  165

Campsites typed 'RV' but with NO RV/Trailer equipment:
  938

Type of use breakdown by campsite type:
                                      Overnight   :       11
  ANCHORAGE                           Overnight   :       13
  BALL FIELD                          Day         :        3
  BOAT IN                             Overnight   :      930
  CABIN ELECTRIC                      Overnight   :      368
  CABIN ELECTRIC                      Day         :        4
  CABIN NONELECTRIC                   Overnight   :      728
  Designated Campsite                 Overnight   :        1
  EQUESTRIAN ELECTRIC                 Overnight   :      270
  EQUESTRIAN NONELECTRIC              Overnight   :    1,068
  GROUP EQUESTRIAN                    Overnight   :       29
  GROUP HIKE TO                       Overnight   :       18
  GROUP PICNIC AREA                   Day         :      346
  GROUP PICNIC AREA                   Overnight   :        4
  GROUP RV AREA NONELECTRIC           Overnight   :       36
  GROUP SHELTER ELECTRIC              Day         :      794
  GROUP SHELTER ELECTRIC              Overnight   :       23
  GROUP SHELTER NONELECTRIC           Day         :      279
  GROUP SHELTER NONELECTRIC           Overnight   :       55
  GROUP STANDARD AREA ELECTRIC        Overnight   :       25
  GROUP STANDARD AREA ELECTRIC        Day         :        1
  GROUP STANDARD AREA NONELECTRIC     Day         :      326
  GROUP STANDARD AREA NONELECTRIC     Overnight   :      222
  GROUP STANDARD ELECTRIC             Overnight   :      216
  GROUP STANDARD ELECTRIC             Day         :       19
  GROUP STANDARD NONELECTRIC          Overnight   :    1,266
  GROUP STANDARD NONELECTRIC          Day         :        4
  GROUP TENT ONLY AREA NONELECTRIC    Overnight   :      591
  GROUP WALK TO                       Overnight   :       43
  GROUP WALK TO                       Day         :        4
  HIKE TO                             Overnight   :      570
  HIKE TO                             multi       :        1
  LOOKOUT                             Overnight   :       20
  LOOKOUT                             Day         :        4
  MANAGEMENT                          Overnight   :   10,772
  MANAGEMENT                          Day         :      177
  MOORING                             Day         :      200
  MOORING                             Overnight   :       59
  OVERNIGHT SHELTER ELECTRIC          Overnight   :      150
  OVERNIGHT SHELTER NONELECTRIC       Overnight   :       81
  PARKING                             Day         :      368
  PARKING                             Overnight   :      218
  PICNIC                              Day         :      430
  PICNIC                              Overnight   :        8
  RV ELECTRIC                         Overnight   :    3,045
  RV NONELECTRIC                      Overnight   :    3,298
  SHELTER ELECTRIC                    Day         :       11
  SHELTER ELECTRIC                    Overnight   :        2
  SHELTER NONELECTRIC                 Overnight   :       87
  SHELTER NONELECTRIC                 Day         :       30
  STANDARD ELECTRIC                   Overnight   :   33,386
  STANDARD NONELECTRIC                Overnight   :   60,285
  STANDARD NONELECTRIC                Day         :       16
  TENT ONLY ELECTRIC                  Overnight   :      431
  TENT ONLY NONELECTRIC               Overnight   :    9,540
  WALK TO                             Overnight   :    1,983
  WALK TO                             Day         :        2
  YURT                                Overnight   :       79
  Zone                                Overnight   :       24
```
