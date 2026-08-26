const config = JSON.parse(document.getElementById("homepass-config").textContent);
const card = document.getElementById("card");
const eyebrow = document.getElementById("eyebrow");
const title = document.getElementById("title");
const message = document.getElementById("message");
const button = document.getElementById("primary");
const status = document.getElementById("status");
const completionNote = document.getElementById("completion-note");
const trustCopy = document.getElementById("trust-copy");

const devicePresentation = () => {
  const reportedPlatform = navigator.userAgentData?.platform || navigator.platform || "";
  const userAgent = navigator.userAgent || "";
  const iPadDesktopMode = /Mac/i.test(reportedPlatform) && navigator.maxTouchPoints > 1;
  if (/iPhone|iPad|iPod/i.test(userAgent) || /Mac/i.test(reportedPlatform) || iPadDesktopMode) {
    return {
      kind: "apple",
      enrollment: "Create a passkey using Face ID or Touch ID. No HomePASS or Home Assistant app is required.",
      setup: "Set up with Face ID or Touch ID",
      waiting: "Waiting for Face ID or Touch ID…",
    };
  }
  if (/Android/i.test(userAgent) || /Android/i.test(reportedPlatform)) {
    return {
      kind: "android",
      enrollment: "Create a passkey using your fingerprint, face, or screen lock. No HomePASS or Home Assistant app is required.",
      setup: "Set up with your phone",
      waiting: "Waiting for fingerprint, face, or screen lock…",
    };
  }
  return {
    kind: "generic",
    enrollment: "Create a passkey using this device. No HomePASS or Home Assistant app is required.",
    setup: "Set up with your passkey",
    waiting: "Waiting for your passkey…",
  };
};

const device = devicePresentation();
const doorAction = ["open", "close", "unlock"].includes(config.action)
  ? config.action
  : "unlock";
button.dataset.platform = device.kind;
let expired = false;
let completed = false;
let expiryTimer;
let credentialController;

const fromB64 = (value) => {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - normalized.length % 4) % 4);
  return Uint8Array.from(atob(padded), (character) => character.charCodeAt(0)).buffer;
};
const toB64 = (buffer) => {
  let binary = "";
  new Uint8Array(buffer).forEach((value) => { binary += String.fromCharCode(value); });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};
const credentialJSON = (credential) => {
  const response = {clientDataJSON: toB64(credential.response.clientDataJSON)};
  if (credential.response.attestationObject) {
    response.attestationObject = toB64(credential.response.attestationObject);
    response.transports = credential.response.getTransports?.() || [];
  } else {
    response.authenticatorData = toB64(credential.response.authenticatorData);
    response.signature = toB64(credential.response.signature);
    response.userHandle = credential.response.userHandle ? toB64(credential.response.userHandle) : null;
  }
  return {id: credential.id, rawId: toB64(credential.rawId), type: credential.type,
    authenticatorAttachment: credential.authenticatorAttachment,
    clientExtensionResults: credential.getClientExtensionResults(), response};
};
const registrationOptions = (options) => {
  options.challenge = fromB64(options.challenge);
  options.user.id = fromB64(options.user.id);
  (options.excludeCredentials || []).forEach((item) => { item.id = fromB64(item.id); });
  return options;
};
const authenticationOptions = (options) => {
  options.challenge = fromB64(options.challenge);
  (options.allowCredentials || []).forEach((item) => { item.id = fromB64(item.id); });
  return options;
};
const post = async (path, payload) => {
  const response = await fetch(path, {method: "POST", credentials: "omit",
    headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || data.message || "Request failed");
  return data;
};
const succeed = (heading, detail) => {
  completed = true;
  if (expiryTimer) window.clearTimeout(expiryTimer);
  credentialController = undefined;
  card.classList.add("ok"); eyebrow.textContent = "Identity verified";
  title.textContent = heading; message.textContent = detail; message.hidden = false;
  button.hidden = true; status.textContent = "✓ Verified";
  completionNote.hidden = false;
};
const fail = (detail) => {
  card.classList.add("error"); eyebrow.textContent = "Verification needed";
  status.textContent = detail; button.disabled = false; completionNote.hidden = true;
};
const expire = () => {
  if (completed) return;
  expired = true;
  if (credentialController) credentialController.abort();
  card.classList.remove("ok", "error", "test");
  card.classList.add("expired");
  eyebrow.textContent = "NFC tap expired";
  title.textContent = "This page has expired";
  message.textContent = "Tap the NFC tag again to operate the door. You can safely move away from or close this page.";
  message.hidden = false;
  button.disabled = true;
  button.hidden = true;
  completionNote.hidden = true;
  status.textContent = "No door command sent";
  trustCopy.textContent = "Expired pages cannot be used to operate a door.";
};
const enroll = async () => {
  button.disabled = true; status.textContent = device.waiting;
  try {
    const options = await post("/api/homepass/nfc/passkey/register/options",
      {inviteToken: config.inviteToken});
    const credential = await navigator.credentials.create(
      {publicKey: registrationOptions(options.publicKey)});
    await post("/api/homepass/nfc/passkey/register/complete",
      {ceremony: options.ceremony, credential: credentialJSON(credential)});
    succeed("You’re all set", "Your device passkey can now verify your HomePASS access at NFC doors.");
  } catch (error) { fail(error.message || "Enrollment was cancelled."); }
};
const operateDoor = async () => {
  if (expired) return;
  button.disabled = true; status.textContent = device.waiting;
  credentialController = new AbortController();
  try {
    const options = await post("/api/homepass/nfc/passkey/authenticate/options",
      {tapSession: config.tapSession});
    const credential = await navigator.credentials.get(
      {publicKey: authenticationOptions(options.publicKey), signal: credentialController.signal});
    const result = await post("/api/homepass/nfc/passkey/authenticate/complete",
      {ceremony: options.ceremony, credential: credentialJSON(credential)});
    const successHeading = result.action === "close"
      ? "Door closing"
      : result.action === "open"
        ? "Door opening"
        : "Access approved";
    succeed(successHeading, result.message);
  } catch (error) {
    if (expired || error.name === "AbortError") return;
    if (/expired|tap again/i.test(error.message || "")) {
      expire();
      return;
    }
    fail(error.message || "Access could not be verified.");
  }
};

if (!window.PublicKeyCredential) {
  eyebrow.textContent = "Passkey unavailable";
  title.textContent = "Passkeys unavailable";
  message.textContent = "This phone or browser cannot use passkeys.";
  message.hidden = false;
  button.hidden = true;
} else if (config.mode === "enroll") {
  eyebrow.textContent = "Secure enrollment";
  title.textContent = "Set up HomePASS";
  message.textContent = device.enrollment;
  message.hidden = false;
  button.textContent = device.setup; button.disabled = false;
  button.addEventListener("click", enroll);
} else if (config.mode === "unlock") {
  if (config.testMode) card.classList.add("test");
  eyebrow.textContent = config.testMode ? "NTAG216 test access" : "Secure NFC access";
  title.textContent = config.door;
  message.textContent = ""; message.hidden = true;
  button.textContent = `Click here to ${doorAction} the door`; button.disabled = false;
  button.addEventListener("click", operateDoor);
  expiryTimer = window.setTimeout(expire, Number(config.expiresInMs) || 30_000);
} else {
  card.classList.add("error"); eyebrow.textContent = "Secure access";
  title.textContent = "Access unavailable";
  message.textContent = "This NFC tap could not be verified. Please tap the tag again.";
  message.hidden = false;
  button.hidden = true; status.textContent = "Not unlocked";
}
