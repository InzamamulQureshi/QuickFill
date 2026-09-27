/**
 * Quick Fill (QF) - Interactive Application Logic
 * Supports webcam capture, file drag-and-drop, real-time age computation,
 * multi-card smart merging, light/dark themes, and minimal UI states.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Theme Switching
  const themeToggleBtn = document.getElementById("themeToggleBtn");
  const storedTheme = localStorage.getItem("qf-theme") || "dark";
  applyTheme(storedTheme);

  function applyTheme(theme) {
    if (theme === "light") {
      document.body.classList.remove("dark-theme");
      document.body.classList.add("light-theme");
      localStorage.setItem("qf-theme", "light");
    } else {
      document.body.classList.remove("light-theme");
      document.body.classList.add("dark-theme");
      localStorage.setItem("qf-theme", "dark");
    }
  }

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", () => {
      const isLight = document.body.classList.contains("light-theme");
      applyTheme(isLight ? "dark" : "light");
    });
  }

  // DOM Elements - Tabs & Studio
  const tabUploadBtn = document.getElementById("tabUploadBtn");
  const tabCameraBtn = document.getElementById("tabCameraBtn");
  const uploadView = document.getElementById("uploadView");
  const cameraView = document.getElementById("cameraView");
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const browseFileBtn = document.getElementById("browseFileBtn");

  // Camera Elements
  const webcamVideo = document.getElementById("webcamVideo");
  const shutterBtn = document.getElementById("shutterBtn");
  const stopCameraBtn = document.getElementById("stopCameraBtn");
  const snapshotCanvas = document.getElementById("snapshotCanvas");
  let cameraStream = null;

  // Preview Elements
  const previewContainer = document.getElementById("previewContainer");
  const previewImage = document.getElementById("previewImage");
  const detectedDocBadge = document.getElementById("detectedDocBadge");
  const ocrTimeMeta = document.getElementById("ocrTimeMeta");
  const ocrLinesMeta = document.getElementById("ocrLinesMeta");
  const toggleRawTextBtn = document.getElementById("toggleRawTextBtn");
  const rawTextInspector = document.getElementById("rawTextInspector");

  // Form Fields
  const form = document.getElementById("quickFillForm");
  const inputName = document.getElementById("fullName");
  const inputDob = document.getElementById("dateOfBirth");
  const inputAge = document.getElementById("calculatedAge");
  const inputFatherSpouse = document.getElementById("fatherSpouseName");
  const inputAddress = document.getElementById("fullAddress");
  const inputIdNumber = document.getElementById("idNumber");
  const inputGender = document.getElementById("gender");

  // Badges & Chips
  const badgeName = document.getElementById("badgeName");
  const badgeDob = document.getElementById("badgeDob");
  const badgeFatherSpouse = document.getElementById("badgeFatherSpouse");
  const badgeAddress = document.getElementById("badgeAddress");
  const chipState = document.getElementById("chipState");
  const chipPincode = document.getElementById("chipPincode");
  const mergeStatusIndicator = document.getElementById("mergeStatusIndicator");

  // Actions & Modals
  const submitFormBtn = document.getElementById("submitFormBtn");
  const exportJsonBtn = document.getElementById("exportJsonBtn");
  const resetFormBtn = document.getElementById("resetFormBtn");
  const toastNotification = document.getElementById("toastNotification");
  const toastTitle = document.getElementById("toastTitle");
  const toastMessage = document.getElementById("toastMessage");
  const infoBtn = document.getElementById("infoBtn");
  const infoModal = document.getElementById("infoModal");
  const closeModalBtn = document.getElementById("closeModalBtn");
  const engineLabel = document.getElementById("engineLabel");

  // Sample card buttons
  const samplePills = document.querySelectorAll(".sample-pill");

  // Form state
  const formState = {
    fullName: "",
    dateOfBirth: "",
    calculatedAge: "",
    fatherSpouseName: "",
    fullAddress: "",
    idNumber: "",
    gender: "",
    state: "",
    pincode: "",
    documentsScanned: []
  };

  /* --------------------------------------------------------------------------
     1. Status Check & Initialization
     -------------------------------------------------------------------------- */
  async function checkBackendStatus() {
    try {
      const res = await fetch("/api/status");
      if (res.ok) {
        const data = await res.json();
        const primary = data.ocr_engines?.primary_engine || "winocr";
        if (primary === "winocr") {
          engineLabel.textContent = "Windows Native OCR";
        } else if (primary === "tesseract") {
          engineLabel.textContent = "Tesseract 5 OCR";
        } else {
          engineLabel.textContent = "Local OCR Ready";
        }
      }
    } catch (e) {
      engineLabel.textContent = "Connecting...";
    }
  }
  checkBackendStatus();

  /* --------------------------------------------------------------------------
     2. Tab Switching (Upload vs Camera)
     -------------------------------------------------------------------------- */
  tabUploadBtn.addEventListener("click", () => {
    tabUploadBtn.classList.add("active");
    tabCameraBtn.classList.remove("active");
    uploadView.style.display = "block";
    cameraView.style.display = "none";
    stopCamera();
  });

  tabCameraBtn.addEventListener("click", () => {
    tabCameraBtn.classList.add("active");
    tabUploadBtn.classList.remove("active");
    uploadView.style.display = "none";
    cameraView.style.display = "block";
    startCamera();
  });

  /* --------------------------------------------------------------------------
     3. Camera Stream Handling
     -------------------------------------------------------------------------- */
  async function startCamera() {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        cameraStream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "environment",
            width: { ideal: 1920 },
            height: { ideal: 1080 }
          }
        });
        webcamVideo.srcObject = cameraStream;
      } else {
        showToast("Camera Error", "Webcam access is not supported by your browser.");
      }
    } catch (err) {
      console.error("Camera access failed:", err);
      showToast("Camera Access Denied", "Please allow camera access or use file upload.");
    }
  }

  function stopCamera() {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      cameraStream = null;
      webcamVideo.srcObject = null;
    }
  }

  stopCameraBtn.addEventListener("click", () => {
    stopCamera();
    tabUploadBtn.click();
  });

  shutterBtn.addEventListener("click", () => {
    if (!webcamVideo.videoWidth) {
      showToast("Camera Not Ready", "Please wait for video stream to initialize.");
      return;
    }

    snapshotCanvas.width = webcamVideo.videoWidth;
    snapshotCanvas.height = webcamVideo.videoHeight;
    const ctx = snapshotCanvas.getContext("2d");
    ctx.drawImage(webcamVideo, 0, 0, snapshotCanvas.width, snapshotCanvas.height);

    const base64Data = snapshotCanvas.toDataURL("image/jpeg", 0.95);
    displayPreview(base64Data);

    stopCamera();
    uploadView.style.display = "block";
    cameraView.style.display = "none";
    tabUploadBtn.classList.add("active");
    tabCameraBtn.classList.remove("active");

    processImageExtraction(base64Data, true);
  });

  /* --------------------------------------------------------------------------
     4. File Upload & Drag-and-Drop
     -------------------------------------------------------------------------- */
  browseFileBtn.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("click", (e) => {
    if (e.target !== browseFileBtn) fileInput.click();
  });

  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) handleFile(file);
  });

  ["dragenter", "dragover"].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(name => {
    dropzone.addEventListener(name, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });

  function handleFile(file) {
    if (!file.type.startsWith("image/") && !file.name.endsWith(".pdf")) {
      showToast("Unsupported Format", "Please provide a valid image file (JPG, PNG, WEBP).");
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target.result;
      displayPreview(dataUrl);
      processImageExtraction(file, false);
    };
    reader.readAsDataURL(file);
  }

  function displayPreview(src) {
    previewImage.src = src;
    previewContainer.style.display = "block";
    detectedDocBadge.textContent = "Scanning...";
  }

  /* --------------------------------------------------------------------------
     5. OCR Extraction & Form Filling API Call
     -------------------------------------------------------------------------- */
  async function processImageExtraction(imageSource, isBase64) {
    const formData = new FormData();
    if (isBase64) {
      formData.append("image_data", imageSource);
    } else {
      formData.append("file", imageSource);
    }
    formData.append("doc_hint", "auto");
    formData.append("engine", "auto");

    try {
      const res = await fetch("/api/extract", {
        method: "POST",
        body: formData
      });

      const result = await res.json();

      if (res.ok && result.success) {
        handleExtractionSuccess(result);
      } else {
        detectedDocBadge.textContent = "Extraction Error";
        showToast("Extraction Failed", result.error || "Could not read ID document.");
      }
    } catch (err) {
      console.error("API error:", err);
      showToast("Network Error", "Could not reach backend extraction service.");
    }
  }

  /* --------------------------------------------------------------------------
     6. Intelligent Form Population & Smart Merging
     -------------------------------------------------------------------------- */
  function handleExtractionSuccess(response) {
    const data = response.data;
    const meta = response.ocr_meta || {};
    const docType = response.detected_type || data.card_type || "Detected ID";

    detectedDocBadge.textContent = docType;
    ocrTimeMeta.textContent = `Speed: ${meta.processing_time_ms || 0} ms`;
    ocrLinesMeta.textContent = `Lines: ${meta.lines_count || 0}`;

    rawTextInspector.textContent = meta.raw_text || "(No text detected)";

    if (!formState.documentsScanned.includes(docType)) {
      formState.documentsScanned.push(docType);
    }

    // Name
    if (data.name) {
      inputName.value = data.name;
      formState.fullName = data.name;
      setFieldPopulated(inputName, badgeName, `From ${docType}`);
    }

    // DOB & Age
    if (data.dob) {
      inputDob.value = data.dob;
      formState.dateOfBirth = data.dob;
      setFieldPopulated(inputDob, badgeDob, `From ${docType}`);

      if (data.age && data.age.formatted) {
        inputAge.value = data.age.formatted;
        formState.calculatedAge = data.age.formatted;
        inputAge.classList.add("field-populated");
      }
    }

    // Father / Spouse
    if (data.father_spouse_name) {
      inputFatherSpouse.value = data.father_spouse_name;
      formState.fatherSpouseName = data.father_spouse_name;
      setFieldPopulated(inputFatherSpouse, badgeFatherSpouse, `From ${docType}`);
    }

    // Address
    if (data.address) {
      inputAddress.value = data.address;
      formState.fullAddress = data.address;
      setFieldPopulated(inputAddress, badgeAddress, `From ${docType}`);

      if (data.state) {
        chipState.textContent = `State: ${data.state}`;
        chipState.style.display = "inline-block";
        formState.state = data.state;
      }
      if (data.pincode) {
        chipPincode.textContent = `PIN: ${data.pincode}`;
        chipPincode.style.display = "inline-block";
        formState.pincode = data.pincode;
      }
    }

    // ID Number
    const idVal = data.aadhaar_number || data.pan_number;
    if (idVal) {
      inputIdNumber.value = idVal;
      formState.idNumber = idVal;
      inputIdNumber.classList.add("field-populated");
    }

    // Gender
    if (data.gender) {
      inputGender.value = data.gender;
      formState.gender = data.gender;
      inputGender.classList.add("field-populated");
    }

    // Smart Merge indicator
    if (formState.documentsScanned.length > 1) {
      mergeStatusIndicator.textContent = `Merged (${formState.documentsScanned.join(" + ")})`;
      showToast("Smart Merged", `Merged details from ${docType}.`);
    } else {
      showToast("Extracted", `Populated form from ${docType}.`);
    }
  }

  function setFieldPopulated(inputEl, badgeEl, badgeText) {
    inputEl.classList.remove("field-populated");
    void inputEl.offsetWidth;
    inputEl.classList.add("field-populated");

    if (badgeEl) {
      badgeEl.textContent = badgeText;
      badgeEl.classList.add("auto-filled");
    }
  }

  /* --------------------------------------------------------------------------
     7. Dynamic Age Calculation on Manual DOB Input
     -------------------------------------------------------------------------- */
  inputDob.addEventListener("input", (e) => {
    const val = e.target.value.trim();
    if (val.length >= 4) {
      computeAgeClientSide(val);
    } else {
      inputAge.value = "";
    }
  });

  function computeAgeClientSide(dobString) {
    const clean = dobString.replace(/['"`|\\.]/g, "/").replace(/[-_\s]/g, "/");
    const parts = clean.split("/");

    let parsedDate = null;
    if (parts.length === 3) {
      const d = parseInt(parts[0], 10);
      const m = parseInt(parts[1], 10);
      const y = parseInt(parts[2], 10);
      if (d >= 1 && d <= 31 && m >= 1 && m <= 12 && y >= 1900 && y <= 2030) {
        parsedDate = new Date(y, m - 1, d);
      }
    } else if (/^\d{4}$/.test(dobString)) {
      parsedDate = new Date(parseInt(dobString, 10), 0, 1);
    }

    if (!parsedDate || isNaN(parsedDate.getTime())) {
      inputAge.value = "Enter DD/MM/YYYY";
      return;
    }

    const today = new Date();
    let years = today.getFullYear() - parsedDate.getFullYear();
    let months = today.getMonth() - parsedDate.getMonth();
    let days = today.getDate() - parsedDate.getDate();

    if (days < 0) {
      months--;
      const prevMonth = new Date(today.getFullYear(), today.getMonth(), 0);
      days += prevMonth.getDate();
    }
    if (months < 0) {
      years--;
      months += 12;
    }

    if (years >= 0) {
      inputAge.value = `${years} Years${months > 0 ? `, ${months} Months` : ""}`;
    } else {
      inputAge.value = "Future Date";
    }
  }

  /* --------------------------------------------------------------------------
     8. 1-Click Instant Demo Cards
     -------------------------------------------------------------------------- */
  samplePills.forEach(pill => {
    pill.addEventListener("click", async () => {
      const sampleType = pill.getAttribute("data-sample");
      pill.style.opacity = "0.5";
      displayPreview(`/api/samples/${sampleType}`);

      try {
        const response = await fetch(`/api/samples/${sampleType}`);
        const blob = await response.blob();
        pill.style.opacity = "1";
        processImageExtraction(blob, false);
      } catch (err) {
        pill.style.opacity = "1";
        showToast("Sample Error", "Could not load demo card.");
      }
    });
  });

  /* --------------------------------------------------------------------------
     9. Form Actions (Submit, Export JSON, Reset)
     -------------------------------------------------------------------------- */
  submitFormBtn.addEventListener("click", () => {
    if (!inputName.value.trim()) {
      showToast("Missing Name", "Please provide a name before submitting.");
      inputName.focus();
      return;
    }

    showToast("Submitted", "Application details successfully validated and saved.");
  });

  exportJsonBtn.addEventListener("click", () => {
    const payload = {
      fullName: inputName.value.trim(),
      dateOfBirth: inputDob.value.trim(),
      calculatedAge: inputAge.value.trim(),
      fatherSpouseName: inputFatherSpouse.value.trim(),
      fullAddress: inputAddress.value.trim(),
      idNumber: inputIdNumber.value.trim(),
      gender: inputGender.value.trim(),
      state: chipState.style.display !== "none" ? chipState.textContent.replace("State: ", "") : "",
      pincode: chipPincode.style.display !== "none" ? chipPincode.textContent.replace("PIN: ", "") : "",
      documentsScanned: formState.documentsScanned,
      exportedAt: new Date().toISOString()
    };

    const jsonString = JSON.stringify(payload, null, 2);

    navigator.clipboard.writeText(jsonString).then(() => {
      showToast("Exported", "KYC JSON copied to clipboard.");
    }).catch(() => {
      const blob = new Blob([jsonString], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `QF_KYC_${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Downloaded", "KYC JSON saved to file.");
    });
  });

  resetFormBtn.addEventListener("click", () => {
    form.reset();
    inputAge.value = "";
    chipState.style.display = "none";
    chipPincode.style.display = "none";
    previewContainer.style.display = "none";
    previewImage.src = "";
    rawTextInspector.textContent = "";
    rawTextInspector.style.display = "none";
    mergeStatusIndicator.textContent = "Auto-Merge Ready";
    formState.documentsScanned = [];

    [badgeName, badgeDob, badgeFatherSpouse, badgeAddress].forEach(b => {
      b.textContent = "Manual";
      b.classList.remove("auto-filled");
    });

    showToast("Reset", "All fields cleared.");
  });

  toggleRawTextBtn.addEventListener("click", () => {
    if (rawTextInspector.style.display === "none") {
      rawTextInspector.style.display = "block";
      toggleRawTextBtn.textContent = "Hide OCR Text";
    } else {
      rawTextInspector.style.display = "none";
      toggleRawTextBtn.textContent = "View OCR Text";
    }
  });

  infoBtn.addEventListener("click", () => infoModal.style.display = "flex");
  closeModalBtn.addEventListener("click", () => infoModal.style.display = "none");
  infoModal.addEventListener("click", (e) => {
    if (e.target === infoModal) infoModal.style.display = "none";
  });

  /* --------------------------------------------------------------------------
     10. Toast Notification
     -------------------------------------------------------------------------- */
  let toastTimer = null;
  function showToast(title, message) {
    if (toastTimer) clearTimeout(toastTimer);
    toastTitle.textContent = title;
    toastMessage.textContent = message;

    toastNotification.classList.add("show");
    toastTimer = setTimeout(() => {
      toastNotification.classList.remove("show");
    }, 3200);
  }
});
