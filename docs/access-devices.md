# Doors and Devices

HomePASS treats a **Door** as the durable access boundary. Locks, garage controllers,
relays, keypads, and future readers are devices associated with that Door. Replacing or
renaming a physical device does not create a different access policy.

## Frient KEPZB-110 rollout

1. Pair the keypad with Home Assistant through ZHA.
2. In HomePASS, open **Doors & Devices**, choose **Add Device**, and associate the keypad
   with its Door.
3. HomePASS records the keypad as **Awaiting hardware test**. It does not listen for PINs or
   operate the Door at this stage.
4. Capture representative real ZHA events for a valid PIN, invalid PIN, Disarm, each Arm
   function, and Emergency. Confirm the event fields that identify the originating keypad,
   entered code, and selected function.
5. Add the ZHA event adapter with strict source filtering, centralized HomePASS authorization,
   redacted PIN handling, bounded retries, and username-attributed Activity.
6. Test successful, denied, disabled-User, expired-schedule, offline-Door, and duplicate-event
   cases before marking the keypad **Ready**.

The initial conservative button policy maps Disarm to Unlock and Arm All Zones to Lock. Day,
Night, and Emergency perform no action until deliberately configured and tested.
