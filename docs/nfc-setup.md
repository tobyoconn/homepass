# NFC setup

Select **Set up NFC tag** on a Door, or **Create NFC enrollment** for a User.
If NFC is not yet configured, HomePASS asks Home Assistant for its Nabu Casa
HTTPS address, saves it, and continues setup once NFC is ready. No address needs
to be copied when Home Assistant Cloud remote access is available.

If the address cannot be found, enable Remote access under **Settings → Home
Assistant Cloud** and choose **Try automatic setup again**, or enter the secure
public HTTPS address manually. A local address is never selected automatically.
Manual addresses must contain no path, query, fragment or sign-in details.

An address already saved for NFC is reused without a Cloud lookup or replacement.
This keeps existing physical tags and passkeys tied to the same origin. Merely
starting HomePASS does not enable NFC; setup requires an administrator action.
The integration's provider options remain available for deliberate configuration
changes. Choose **NFC access** to review this address independently from the
**Nuki keypad** connection. When no address has been saved, the NFC form obtains
and pre-fills the Home Assistant Cloud address automatically.

The `homepass.configure_nfc` action accepts an optional `nfc_public_origin` field:
omit it to reuse the saved address or discover Cloud; supply it for manual setup.
An unavailable Cloud address returns `reason: cloud_unavailable` without saving
options or requesting a reload. Successful first-time setup preserves unrelated
options and uses the existing integration reload listener.
