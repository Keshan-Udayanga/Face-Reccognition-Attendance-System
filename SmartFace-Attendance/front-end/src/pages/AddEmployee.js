import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Camera,
  Check,
  CircleAlert,
  FileImage,
  ImagePlus,
  Info,
  Trash2,
  Upload,
  UserRound,
  X,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router";
import {
  createEmployee,
  getEmployeeById,
  updateEmployee,
} from "../services/employeeService";
import "./AddEmployee.css";

const MAX_IMAGE_SIZE_BYTES = 1024 * 1024;
const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png"];
const departmentOptions = [
  "Engineering",
  "Finance",
  "Human Resources",
  "IT Support",
  "Marketing",
  "Operations",
  "Sales",
];

const emptyForm = {
  fullName: "",
  department: "",
  email: "",
  contactNumber: "",
  designation: "",
  address: "",
  photoUrl: "",
};

function validateImage(file) {
  if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
    return "Choose a JPG, JPEG, or PNG image.";
  }
  if (file.size > MAX_IMAGE_SIZE_BYTES) {
    return "This image is larger than 1 MB. Choose a smaller image.";
  }
  return "";
}

function readImageAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("This image could not be read. Try another file."));
    reader.readAsDataURL(file);
  });
}

function getInitials(name = "") {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function validateForm(form) {
  const errors = {};

  if (!form.fullName.trim()) errors.fullName = "Full name is required.";
  if (!form.department) errors.department = "Choose a department.";
  if (!form.email.trim()) {
    errors.email = "Email address is required.";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
    errors.email = "Enter a valid email address.";
  }
  if (!form.contactNumber.trim()) {
    errors.contactNumber = "Contact number is required.";
  } else {
    const digitCount = form.contactNumber.replace(/\D/g, "").length;
    if (
      !/^\+?[\d\s().-]+$/.test(form.contactNumber.trim()) ||
      digitCount < 7 ||
      digitCount > 15
    ) {
      errors.contactNumber = "Enter a valid number containing 7 to 15 digits.";
    }
  }

  return errors;
}

function FormField({
  label,
  name,
  value,
  onChange,
  error,
  required = false,
  ...inputProps
}) {
  const fieldId = `employee-${name}`;
  const errorId = `${fieldId}-error`;

  return (
    <div className={`form-field ${error ? "form-field-invalid" : ""}`}>
      <label htmlFor={fieldId}>
        {label} {required && <span className="required-mark">*</span>}
      </label>
      <input
        aria-describedby={error ? errorId : undefined}
        aria-invalid={Boolean(error)}
        id={fieldId}
        name={name}
        onChange={onChange}
        value={value}
        {...inputProps}
      />
      {error && (
        <span className="field-error" id={errorId}>
          {error}
        </span>
      )}
    </div>
  );
}

export default function AddEmployee() {
  const { employeeId } = useParams();
  const isEditing = Boolean(employeeId);
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const originalPhotoUrl = useRef("");
  const [form, setForm] = useState(emptyForm);
  const [errors, setErrors] = useState({});
  const [imageError, setImageError] = useState("");
  const [formError, setFormError] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingEmployee, setIsLoadingEmployee] = useState(isEditing);

  useEffect(() => {
    if (!isEditing) {
      setForm(emptyForm);
      originalPhotoUrl.current = "";
      setIsLoadingEmployee(false);
      return;
    }

    let isCurrent = true;
    setIsLoadingEmployee(true);
    getEmployeeById(employeeId)
      .then((employee) => {
        if (!isCurrent) return;
        if (!employee) {
          setIsLoadingEmployee(false);
          navigate("/employees", {
            replace: true,
            state: { notice: "That employee could not be found." },
          });
          return;
        }

        const photoUrl = employee.photoUrl || "";
        originalPhotoUrl.current = photoUrl;
        setForm({
          employeeId: employee.employeeId || "",
          fullName: employee.fullName || "",
          department: employee.department || "",
          email: employee.email || "",
          contactNumber: employee.contactNumber || "",
          designation: employee.designation || "",
          address: employee.address || "",
          photoUrl,
        });
        setIsLoadingEmployee(false);
      })
      .catch((loadError) => {
        if (isCurrent) {
          setFormError(loadError.message);
          setIsLoadingEmployee(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [employeeId, isEditing, navigate]);

  function handleChange(event) {
    const { name, value } = event.target;
    setForm((currentForm) => ({ ...currentForm, [name]: value }));
    setErrors((currentErrors) => ({ ...currentErrors, [name]: "" }));
    setFormError("");
  }

  async function handleImageFile(file) {
    setImageError("");
    if (!file) return;

    const validationError = validateImage(file);
    if (validationError) {
      setImageError(validationError);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    try {
      const photoUrl = await readImageAsDataUrl(file);
      setForm((currentForm) => ({ ...currentForm, photoUrl }));
    } catch (readError) {
      setImageError(readError.message);
    }
  }

  function handleFileChange(event) {
    handleImageFile(event.target.files?.[0]);
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    handleImageFile(event.dataTransfer.files?.[0]);
  }

  function removeImage() {
    setForm((currentForm) => ({ ...currentForm, photoUrl: "" }));
    setImageError("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function resetForm() {
    setErrors({});
    setImageError("");
    setFormError("");
    if (isEditing) {
      try {
        const employee = await getEmployeeById(employeeId);
        if (employee) {
          const photoUrl = employee.photoUrl || "";
          originalPhotoUrl.current = photoUrl;
          setForm({
            employeeId: employee.employeeId || "",
            fullName: employee.fullName || "",
            department: employee.department || "",
            email: employee.email || "",
            contactNumber: employee.contactNumber || "",
            designation: employee.designation || "",
            address: employee.address || "",
            photoUrl,
          });
        }
      } catch (loadError) {
        setFormError(loadError.message);
      }
    } else {
      setForm(emptyForm);
      originalPhotoUrl.current = "";
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    if (isLoadingEmployee) return;
    setIsSaving(true);

    const nextErrors = validateForm(form);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      setFormError("Please check the highlighted fields and try again.");
      setIsSaving(false);
      return;
    }

    const employeeData = {
      fullName: form.fullName.trim(),
      department: form.department,
      email: form.email.trim(),
      contactNumber: form.contactNumber.trim(),
      designation: form.designation.trim(),
      address: form.address.trim(),
      photoUrl: form.photoUrl,
      removePhoto: isEditing && !form.photoUrl && Boolean(originalPhotoUrl.current),
    };

    try {
      if (isEditing) {
        await updateEmployee(employeeId, employeeData);
        navigate("/employees", {
          state: { notice: `${employeeData.fullName}'s details were updated.` },
        });
      } else {
        const createdEmployee = await createEmployee(employeeData);
        navigate("/employees", {
          state: {
            notice: `${employeeData.fullName} was added successfully. Employee ID: ${createdEmployee.employeeId}.`,
          },
        });
      }
    } catch (saveError) {
      setFormError(saveError.message);
      setIsSaving(false);
    }
  }

  return (
    <div className="page-content add-employee-page">
      <div className="form-page-intro">
        <div>
          <Link className="back-link" to="/employees">
            <ArrowLeft aria-hidden="true" size={15} />
            Back to employees
          </Link>
          <p>
            {isEditing
              ? "Update employee information and profile photo."
              : "Add a new team member to your SmartFace workspace."}
          </p>
        </div>
        <div className="form-required-note">
          <span className="required-mark">*</span> Required fields
        </div>
      </div>

      {formError && (
        <div className="form-error" role="alert">
          <CircleAlert aria-hidden="true" size={18} />
          <span>{formError}</span>
        </div>
      )}

      <form className="employee-form" noValidate onSubmit={handleSubmit}>
        <section className="form-section surface-card photo-section">
          <div className="form-section-heading">
            <span className="form-section-icon">
              <Camera aria-hidden="true" size={18} />
            </span>
            <div>
              <h2>Profile photo</h2>
              <p>Make it easy to recognize your team member</p>
            </div>
            <span className="optional-label">OPTIONAL</span>
          </div>

          <div className="photo-upload-layout">
            <div
              className={`photo-dropzone ${isDragging ? "photo-dropzone-active" : ""} ${form.photoUrl ? "photo-dropzone-has-image" : ""}`}
              onDragEnter={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={(event) => {
                event.preventDefault();
                if (!event.currentTarget.contains(event.relatedTarget)) {
                  setIsDragging(false);
                }
              }}
              onDragOver={(event) => event.preventDefault()}
              onDrop={handleDrop}
            >
              {form.photoUrl ? (
                <img alt="Employee profile preview" className="photo-preview" src={form.photoUrl} />
              ) : (
                <div className="photo-placeholder">
                  <span className="photo-placeholder-icon">
                    <UserRound aria-hidden="true" size={31} strokeWidth={1.6} />
                  </span>
                  <span className="photo-placeholder-text">
                    {form.fullName ? getInitials(form.fullName) : "PROFILE"}
                  </span>
                </div>
              )}
              {form.photoUrl && (
                <button
                  aria-label="Remove profile photo"
                  className="photo-remove-button"
                  onClick={removeImage}
                  title="Remove photo"
                  type="button"
                >
                  <X aria-hidden="true" size={15} />
                </button>
              )}
            </div>

            <div className="photo-upload-copy">
              <h3>{form.photoUrl ? "Looking good!" : "Upload a profile photo"}</h3>
              <p>
                {form.photoUrl
                  ? "This photo will appear in the employee directory."
                  : "Drag and drop an image here, or browse files from your device."}
              </p>
              <div className="photo-action-row">
                <button
                  className="secondary-button upload-button"
                  onClick={() => fileInputRef.current?.click()}
                  type="button"
                >
                  {form.photoUrl ? (
                    <ImagePlus aria-hidden="true" size={16} />
                  ) : (
                    <Upload aria-hidden="true" size={16} />
                  )}
                  {form.photoUrl ? "Change photo" : "Choose image"}
                </button>
                {form.photoUrl && (
                  <button
                    className="photo-remove-text"
                    onClick={removeImage}
                    type="button"
                  >
                    <Trash2 aria-hidden="true" size={14} />
                    Remove
                  </button>
                )}
              </div>
              <input
                accept="image/jpeg,image/png,.jpg,.jpeg,.png"
                className="visually-hidden"
                onChange={handleFileChange}
                ref={fileInputRef}
                type="file"
              />
              <div className="photo-format-note">
                <FileImage aria-hidden="true" size={14} />
                JPG or PNG · Max 1 MB
              </div>
              {imageError && (
                <span className="field-error image-field-error" role="alert">
                  {imageError}
                </span>
              )}
            </div>
          </div>
          <div className="photo-storage-note">
            <Info aria-hidden="true" size={15} />
              A photo is optional. Uploaded images are stored in PostgreSQL.
          </div>
        </section>

        <section className="form-section surface-card details-section">
          <div className="form-section-heading">
            <span className="form-section-icon">
              <UserRound aria-hidden="true" size={18} />
            </span>
            <div>
              <h2>Employee information</h2>
              <p>Enter the employee&apos;s work and contact details</p>
            </div>
          </div>

          {isEditing && !isLoadingEmployee && (
            <div className="generated-employee-id">
              <span>EMPLOYEE ID</span>
              <strong>{form.employeeId}</strong>
              <span>This ID is generated automatically and cannot be changed.</span>
            </div>
          )}

          <div className="employee-fields-grid">
            <FormField
              autoComplete="name"
              error={errors.fullName}
              label="Full Name"
              name="fullName"
              onChange={handleChange}
              placeholder="e.g. Jordan Smith"
              required
              value={form.fullName}
            />
            <div className={`form-field ${errors.department ? "form-field-invalid" : ""}`}>
              <label htmlFor="employee-department">
                Department <span className="required-mark">*</span>
              </label>
              <select
                aria-describedby={errors.department ? "employee-department-error" : undefined}
                aria-invalid={Boolean(errors.department)}
                id="employee-department"
                name="department"
                onChange={handleChange}
                value={form.department}
              >
                <option disabled value="">
                  Select a department
                </option>
                {departmentOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
                {form.department && !departmentOptions.includes(form.department) && (
                  <option value={form.department}>{form.department}</option>
                )}
              </select>
              {errors.department && (
                <span className="field-error" id="employee-department-error">
                  {errors.department}
                </span>
              )}
            </div>
            <FormField
              autoComplete="email"
              error={errors.email}
              label="Email Address"
              name="email"
              onChange={handleChange}
              placeholder="name@company.com"
              required
              type="email"
              value={form.email}
            />
            <FormField
              autoComplete="tel"
              error={errors.contactNumber}
              label="Contact Number"
              name="contactNumber"
              onChange={handleChange}
              placeholder="+1 (555) 000-0000"
              required
              type="tel"
              value={form.contactNumber}
            />
            <FormField
              autoComplete="organization-title"
              label="Designation"
              name="designation"
              onChange={handleChange}
              placeholder="e.g. Product Designer"
              value={form.designation}
            />
            <div className="form-field address-field">
              <label htmlFor="employee-address">Address</label>
              <textarea
                autoComplete="street-address"
                id="employee-address"
                name="address"
                onChange={handleChange}
                placeholder="Street address, city, state"
                rows={3}
                value={form.address}
              />
            </div>
          </div>
        </section>

        <div className="form-footer">
          <div className="form-footer-tip">
            <Info aria-hidden="true" size={15} />
            Employee details are saved to the PostgreSQL database.
          </div>
          <div className="form-actions">
            <button className="secondary-button reset-button" onClick={resetForm} type="button">
              <X aria-hidden="true" size={15} />
              Reset form
            </button>
            <button
              className="secondary-button cancel-button"
              onClick={() => navigate("/employees")}
              type="button"
            >
              Cancel
            </button>
            <button
              className="primary-button save-button"
              disabled={isSaving || isLoadingEmployee}
              type="submit"
            >
              <Check aria-hidden="true" size={17} />
              {isLoadingEmployee
                ? "Loading employee..."
                : isSaving
                ? "Saving..."
                : isEditing
                  ? "Save changes"
                  : "Save Employee"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
