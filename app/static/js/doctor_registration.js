// static/js/doctor_registration.js
document.addEventListener('DOMContentLoaded', function() {
    const doctorForm = document.getElementById('doctor-registration-form');
    const professionalForm = document.getElementById('professional-registration-form');
    const professionSelector = document.getElementById('profession-type');
    const professionField = document.getElementById('profession-field');
    const specialtySelect = document.getElementById('specialty');
    const fcpsSubSpecialty = document.getElementById('fcps-sub-specialty');
    const alliedHealthSubSpecialty = document.getElementById('allied-health-sub-specialty');
    const loadingSpinner = document.createElement('div');
    const imageInput = document.getElementById('doctor-image');
    const resumeInput = document.getElementById('doctor-resume');
    const proImageInput = document.getElementById('pro-profile-picture');
    const proResumeInput = document.getElementById('pro-resume');
    const proCountrySelect = document.getElementById('pro-country');
    const proCNICGroup = document.getElementById('pro-cnic-group');

    const countrySelect = document.getElementById('country');
    const medicalLicenseGroup = document.getElementById('medical-license-group');
    const nationalIdGroup = document.getElementById('national-id-group');
    const medicalLicenseInput = document.getElementById('medical-license');
    const nationalIdInput = document.getElementById('national-id');

    // Initialize loading spinner
    loadingSpinner.className = 'loading-spinner';
    loadingSpinner.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(loadingSpinner);

    // Profession selector handler
    professionSelector.addEventListener('change', function() {
        const selectedProfession = this.value;
        
        if (selectedProfession === 'doctor') {
            doctorForm.style.display = 'block';
            professionalForm.style.display = 'none';
        } else if (selectedProfession) {
            doctorForm.style.display = 'none';
            professionalForm.style.display = 'block';
            professionField.value = selectedProfession;
        } else {
            doctorForm.style.display = 'none';
            professionalForm.style.display = 'none';
        }
    });

    // Country fields configuration
    const countryFields = {
        afghanistan: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Tazkira Number',
                placeholder: 'Enter Tazkira number'
            }
        },
        albania: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal Number',
                placeholder: 'Enter personal ID number'
            }
        },
        algeria: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National Identity Number',
                placeholder: 'Enter national ID number'
            }
        },
        andorra: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        angola: {
            medicalLicense: {
                label: 'Medical Practitioner License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Identity Card Number',
                placeholder: 'Enter ID card number'
            }
        },
        antigua_and_barbuda: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        argentina: {
            medicalLicense: {
                label: 'National Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'DNI',
                placeholder: 'Enter DNI (Documento Nacional de Identidad)'
            }
        },
        armenia: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Passport Number',
                placeholder: 'Enter passport or national ID number'
            }
        },
        australia: {
            medicalLicense: {
                label: 'AHPRA Number',
                placeholder: 'Enter AHPRA registration number'
            },
            nationalId: {
                label: 'Medicare Number',
                placeholder: 'Enter Medicare number'
            }
        },
        austria: {
            medicalLicense: {
                label: 'Medical Registration',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'Personal Number',
                placeholder: 'Enter Austrian national ID number'
            }
        },
        azerbaijan: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'ID Card Number',
                placeholder: 'Enter ID card number'
            }
        },
        bahamas: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National Insurance Number',
                placeholder: 'Enter NIB number'
            }
        },
        bahrain: {
            medicalLicense: {
                label: 'NHRA License Number',
                placeholder: 'Enter NHRA registration number'
            },
            nationalId: {
                label: 'CPR Number',
                placeholder: 'Enter 9-digit CPR number'
            }
        },
        bangladesh: {
            medicalLicense: {
                label: 'BMDC Registration Number',
                placeholder: 'Enter BMDC registration number'
            },
            nationalId: {
                label: 'NID',
                placeholder: 'Enter National ID number'
            }
        },
        barbados: {
            medicalLicense: {
                label: 'Medical Registration',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National Registration Number',
                placeholder: 'Enter national registration number'
            }
        },
        belarus: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal Number',
                placeholder: 'Enter Belarusian personal number'
            }
        },
        belgium: {
            medicalLicense: {
                label: 'INAMI Number',
                placeholder: 'Enter INAMI registration number'
            },
            nationalId: {
                label: 'National Register Number',
                placeholder: 'Enter 11-digit ID number'
            }
        },
        belize: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Social Security Number',
                placeholder: 'Enter SSN'
            }
        },
        benin: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        bhutan: {
            medicalLicense: {
                label: 'BMHC Registration',
                placeholder: 'Enter BMHC registration number'
            },
            nationalId: {
                label: 'CID',
                placeholder: 'Enter Citizen Identity Card number'
            }
        },
        bolivia: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Carnet de Identidad',
                placeholder: 'Enter ID card number'
            }
        },
        bosnia_and_herzegovina: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'JMBG',
                placeholder: 'Enter 13-digit ID number'
            }
        },
        botswana: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Omang Number',
                placeholder: 'Enter Omang ID number'
            }
        },
        brazil: {
            medicalLicense: {
                label: 'CRM Number',
                placeholder: 'Enter CRM registration number'
            },
            nationalId: {
                label: 'CPF Number',
                placeholder: 'Enter 11-digit CPF number'
            }
        },
        brunei: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Identity Card Number',
                placeholder: 'Enter IC number'
            }
        },
        bulgaria: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Unified Civil Number',
                placeholder: 'Enter EGN'
            }
        },
        burkina_faso: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        burundi: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        cabo_verde: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        cambodia: {
            medicalLicense: {
                label: 'Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Identity Card Number',
                placeholder: 'Enter national ID number'
            }
        },
        cameroon: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        canada: {
            medicalLicense: {
                label: 'Medical Council License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Social Insurance Number',
                placeholder: 'Enter SIN (9 digits)'
            }
        },
        "central african republic": {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        chad: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        chile: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'RUN Number',
                placeholder: 'Enter RUN number'
            }
        },
        china: {
            medicalLicense: {
                label: 'Medical Practitioner Number',
                placeholder: 'Enter medical practitioner number'
            },
            nationalId: {
                label: 'Resident Identity Card Number',
                placeholder: 'Enter 18-digit ID number'
            }
        },
        colombia: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Cedula Number',
                placeholder: 'Enter Cedula number'
            }
        },
        comoros: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "congo, democratic republic of the": {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "congo, republic of the": {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "costa rica": {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Cedula Number',
                placeholder: 'Enter Cedula number'
            }
        },
        croatia: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'OIB Number',
                placeholder: 'Enter OIB number'
            }
        },
        cuba: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Carnet de Identidad',
                placeholder: 'Enter Carnet number'
            }
        },
        cyprus: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "czech republic": {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Birth Number',
                placeholder: 'Enter birth number'
            }
        },
        denmark: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'CPR Number',
                placeholder: 'Enter CPR number'
            }
        },
        djibouti: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        dominica: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "dominican republic": {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Cedula Number',
                placeholder: 'Enter Cedula number'
            }
        },
        ecuador: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Cedula Number',
                placeholder: 'Enter Cedula number'
            }
        },
        egypt: {
            medicalLicense: {
                label: 'Medical Syndicate Number',
                placeholder: 'Enter syndicate number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "el salvador": {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'DUI Number',
                placeholder: 'Enter DUI number'
            }
        },
        "equatorial guinea": {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        eritrea: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        estonia: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal ID Number',
                placeholder: 'Enter personal ID number'
            }
        },
        eswatini: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        ethiopia: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "federated states of micronesia": {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        fiji: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'Fiji ID Number',
                placeholder: 'Enter Fiji ID number'
            }
        },
        finland: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal ID Number',
                placeholder: 'Enter personal ID number'
            }
        },
        france: {
            medicalLicense: {
                label: 'RPPS Number',
                placeholder: 'Enter RPPS number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        gabon: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        gambia: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        georgia: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal ID Number',
                placeholder: 'Enter personal ID number'
            }
        },
        germany: {
            medicalLicense: {
                label: 'Medical License (Approbation)',
                placeholder: 'Enter approbation number'
            },
            nationalId: {
                label: 'Personal ID Number',
                placeholder: 'Enter 11-digit ID number'
            }
        },
        ghana: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'Ghana Card Number',
                placeholder: 'Enter Ghana Card number'
            }
        },
        greece: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal ID Number',
                placeholder: 'Enter personal ID number'
            }
        },
        grenada: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        guatemala: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'CUI Number',
                placeholder: 'Enter CUI number'
            }
        },
        guinea: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "guinea-bissau": {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        guyana: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        haiti: {
            medicalLicense: {
                label: 'Medical Practitioner Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'CIN',
                placeholder: 'Enter 10-digit CIN number'
            }
        },
        honduras: {
            medicalLicense: {
                label: 'Colegio Médico de Honduras Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter identity card number'
            }
        },
        hungary: {
            medicalLicense: {
                label: 'Hungarian Medical License',
                placeholder: 'Enter license number'
            },
            nationalId: {
                label: 'Personal Identification Number',
                placeholder: 'Enter personal ID number'
            }
        },
        iceland: {
            medicalLicense: {
                label: 'Icelandic Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Kennitala',
                placeholder: 'Enter 10-digit Kennitala'
            }
        },
        india: {
            medicalLicense: {
                label: 'MCI Registration Number',
                placeholder: 'Enter MCI registration number'
            },
            nationalId: {
                label: 'Aadhaar Number',
                placeholder: 'Enter 12-digit Aadhaar number'
            }
        },
        indonesia: {
            medicalLicense: {
                label: 'STR Number',
                placeholder: 'Enter STR license number'
            },
            nationalId: {
                label: 'KTP Number',
                placeholder: 'Enter 16-digit KTP number'
            }
        },
        iran: {
            medicalLicense: {
                label: 'Iranian Medical Council Number',
                placeholder: 'Enter medical council number'
            },
            nationalId: {
                label: 'Shenasnameh Number',
                placeholder: 'Enter ID number'
            }
        },
        iraq: {
            medicalLicense: {
                label: 'Iraqi Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        ireland: {
            medicalLicense: {
                label: 'IMC Registration Number',
                placeholder: 'Enter IMC registration number'
            },
            nationalId: {
                label: 'PPS Number',
                placeholder: 'Enter PPS number'
            }
        },
        israel: {
            medicalLicense: {
                label: 'Israeli Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Teudat Zehut',
                placeholder: 'Enter Teudat Zehut ID number'
            }
        },
        italy: {
            medicalLicense: {
                label: 'Italian Medical Council Number',
                placeholder: 'Enter medical council number'
            },
            nationalId: {
                label: 'Codice Fiscale',
                placeholder: 'Enter Codice Fiscale'
            }
        },
        jamaica: {
            medicalLicense: {
                label: 'Jamaican Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'TRN Number',
                placeholder: 'Enter TRN number'
            }
        },
        japan: {
            medicalLicense: {
                label: 'Medical Practitioner Registration Number',
                placeholder: 'Enter registration number'
            },
            nationalId: {
                label: 'My Number',
                placeholder: 'Enter 12-digit My Number'
            }
        },
        jordan: {
            medicalLicense: {
                label: 'Jordan Medical Council Number',
                placeholder: 'Enter medical council number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        kazakhstan: {
            medicalLicense: {
                label: 'Kazakhstan Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'IIN',
                placeholder: 'Enter 12-digit IIN number'
            }
        },
        kenya: {
            medicalLicense: {
                label: 'Medical Practitioners and Dentists Council Number',
                placeholder: 'Enter medical council number'
            },
            nationalId: {
                label: 'Kenyan National ID',
                placeholder: 'Enter national ID number'
            }
        },
        kiribati: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        koreaNorth: {
            medicalLicense: {
                label: 'North Korea Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        koreaSouth: {
            medicalLicense: {
                label: 'Korean Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Resident Registration Number',
                placeholder: 'Enter RRN number'
            }
        },
        kosovo: {
            medicalLicense: {
                label: 'Kosovo Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        kuwait: {
            medicalLicense: {
                label: 'Kuwait Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Civil ID',
                placeholder: 'Enter Civil ID number'
            }
        },
        kyrgyzstan: {
            medicalLicense: {
                label: 'Kyrgyz Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal Identification Number',
                placeholder: 'Enter PIN number'
            }
        },
        laos: {
            medicalLicense: {
                label: 'Lao Medical License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        latvia: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal Code',
                placeholder: 'Enter Latvian personal code'
            }
        },
        lebanon: {
            medicalLicense: {
                label: 'Order of Physicians Registration Number',
                placeholder: 'Enter registration number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        lesotho: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        liberia: {
            medicalLicense: {
                label: 'Medical Council Registration Number',
                placeholder: 'Enter registration number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        libya: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        liechtenstein: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal Number',
                placeholder: 'Enter personal number'
            }
        },
        lithuania: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal Code',
                placeholder: 'Enter personal code'
            }
        },
        luxembourg: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National Identification Number',
                placeholder: 'Enter national ID number'
            }
        },
        madagascar: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        malawi: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        malaysia: {
            medicalLicense: {
                label: 'MMC Registration Number',
                placeholder: 'Enter MMC registration number'
            },
            nationalId: {
                label: 'MyKad Number',
                placeholder: 'Enter 12-digit MyKad number'
            }
        },
        maldives: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Card Number',
                placeholder: 'Enter national ID card number'
            }
        },
        mali: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        malta: {
            medicalLicense: {
                label: 'Medical Council Registration Number',
                placeholder: 'Enter registration number'
            },
            nationalId: {
                label: 'ID Card Number',
                placeholder: 'Enter ID card number'
            }
        },
        'marshall islands': {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        mauritania: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        mauritius: {
            medicalLicense: {
                label: 'Medical Council Registration Number',
                placeholder: 'Enter registration number'
            },
            nationalId: {
                label: 'National ID Card Number',
                placeholder: 'Enter national ID card number'
            }
        },
        mexico: {
            medicalLicense: {
                label: 'Cédula Profesional',
                placeholder: 'Enter cédula number'
            },
            nationalId: {
                label: 'CURP',
                placeholder: 'Enter CURP'
            }
        },
        moldova: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal ID Number',
                placeholder: 'Enter personal ID number'
            }
        },
        monaco: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        mongolia: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        montenegro: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal ID Number',
                placeholder: 'Enter personal ID number'
            }
        },
        morocco: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'CIN',
                placeholder: 'Enter CIN'
            }
        },
        mozambique: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        'myanmar (formerly burma)': {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National Registration Card Number',
                placeholder: 'Enter NRC number'
            }
        },
        namibia: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        nauru: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        nepal: {
            medicalLicense: {
                label: 'NMC Registration Number',
                placeholder: 'Enter NMC registration number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        netherlands: {
            medicalLicense: {
                label: 'BIG Number',
                placeholder: 'Enter BIG registration number'
            },
            nationalId: {
                label: 'BSN',
                placeholder: 'Enter BSN'
            }
        },
        'new zealand': {
            medicalLicense: {
                label: 'MCNZ Registration Number',
                placeholder: 'Enter MCNZ registration number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        nicaragua: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        niger: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID',
                placeholder: 'Enter national ID number'
            }
        },
        nigeria: {
            medicalLicense: {
                label: 'MDCN Registration Number',
                placeholder: 'Enter MDCN registration number'
            },
            nationalId: {
                label: 'NIN',
                placeholder: 'Enter NIN (11 digits)'
            }
        },
        "north macedonia": {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        norway: {
            medicalLicense: {
                label: 'Autorisasjon ID',
                placeholder: 'Enter authorization ID'
            },
            nationalId: {
                label: 'Fødselsnummer',
                placeholder: 'Enter 11-digit Fødselsnummer'
            }
        },
        oman: {
            medicalLicense: {
                label: 'MOH License Number',
                placeholder: 'Enter MOH license number'
            },
            nationalId: {
                label: 'Civil ID Number',
                placeholder: 'Enter civil ID number'
            }
        },
        pakistan: {
            medicalLicense: {
                label: 'PMDC Number',
                placeholder: 'Enter PMDC number'
            },
            nationalId: {
                label: 'CNIC Number',
                placeholder: 'Enter CNIC (without dashes)'
            }
        },
        palau: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        panama: {
            medicalLicense: {
                label: 'CSS License Number',
                placeholder: 'Enter CSS license number'
            },
            nationalId: {
                label: 'Cedula Number',
                placeholder: 'Enter cedula number'
            }
        },
        "papua new guinea": {
            medicalLicense: {
                label: 'Medical Council License',
                placeholder: 'Enter medical council license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        paraguay: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Cedula Number',
                placeholder: 'Enter cedula number'
            }
        },
        peru: {
            medicalLicense: {
                label: 'CMP Number',
                placeholder: 'Enter CMP number'
            },
            nationalId: {
                label: 'DNI Number',
                placeholder: 'Enter DNI number'
            }
        },
        philippines: {
            medicalLicense: {
                label: 'PRC License Number',
                placeholder: 'Enter PRC license number'
            },
            nationalId: {
                label: 'PhilSys Number',
                placeholder: 'Enter 12-digit PhilSys number'
            }
        },
        poland: {
            medicalLicense: {
                label: 'PWZ Number',
                placeholder: 'Enter PWZ number'
            },
            nationalId: {
                label: 'PESEL Number',
                placeholder: 'Enter 11-digit PESEL number'
            }
        },
        portugal: {
            medicalLicense: {
                label: 'OM Number',
                placeholder: 'Enter OM number'
            },
            nationalId: {
                label: 'NIF',
                placeholder: 'Enter 9-digit NIF'
            }
        },
        qatar: {
            medicalLicense: {
                label: 'QCHP License Number',
                placeholder: 'Enter QCHP license number'
            },
            nationalId: {
                label: 'QID',
                placeholder: 'Enter Qatar ID number'
            }
        },
        romania: {
            medicalLicense: {
                label: 'CMB Number',
                placeholder: 'Enter CMB number'
            },
            nationalId: {
                label: 'CNP Number',
                placeholder: 'Enter 13-digit CNP'
            }
        },
        russia: {
            medicalLicense: {
                label: 'Medical Practice Certificate',
                placeholder: 'Enter medical practice certificate number'
            },
            nationalId: {
                label: 'SNILS',
                placeholder: 'Enter SNILS number'
            }
        },
        rwanda: {
            medicalLicense: {
                label: 'Medical Council Number',
                placeholder: 'Enter medical council number'
            },
            nationalId: {
                label: 'NIDA',
                placeholder: 'Enter 16-digit NIDA number'
            }
        },
        "st kitts and nevis": {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "st lucia": {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "st vincent and the grenadines": {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        samoa: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "san marino": {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "sao tome and principe": {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        "saudi arabia": {
            medicalLicense: {
                label: 'SCFHS License Number',
                placeholder: 'Enter SCFHS license number'
            },
            nationalId: {
                label: 'Iqama Number',
                placeholder: 'Enter Iqama or National ID number'
            }
        },
        senegal: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        serbia: {
            medicalLicense: {
                label: 'Medical Chamber Number',
                placeholder: 'Enter medical chamber number'
            },
            nationalId: {
                label: 'Unique Master Citizen Number',
                placeholder: 'Enter 13-digit ID number'
            }
        },
        seychelles: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National Identity Number',
                placeholder: 'Enter national identity number'
            }
        },
        'sierra leone': {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        singapore: {
            medicalLicense: {
                label: 'SMC Registration Number',
                placeholder: 'Enter SMC registration number'
            },
            nationalId: {
                label: 'NRIC/FIN',
                placeholder: 'Enter NRIC or FIN (e.g., S1234567D)'
            }
        },
        slovakia: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        slovenia: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal ID Number',
                placeholder: 'Enter Slovenian personal ID number'
            }
        },
        'solomon islands': {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        somalia: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        'south africa': {
            medicalLicense: {
                label: 'HPCSA Registration Number',
                placeholder: 'Enter HPCSA registration number'
            },
            nationalId: {
                label: 'RSA ID Number',
                placeholder: 'Enter 13-digit ID number'
            }
        },
        'south sudan': {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        spain: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'DNI/NIE',
                placeholder: 'Enter DNI or NIE (e.g., X1234567A)'
            }
        },
        'sri lanka': {
            medicalLicense: {
                label: 'SLMC Registration Number',
                placeholder: 'Enter SLMC registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        sudan: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        suriname: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        sweden: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal Identity Number',
                placeholder: 'Enter 10 or 12-digit personal number'
            }
        },
        switzerland: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Swiss Identity Card Number',
                placeholder: 'Enter Swiss ID card number'
            }
        },
        syria: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        taiwan: {
            medicalLicense: {
                label: 'Medical Practitioner License',
                placeholder: 'Enter medical practitioner license number'
            },
            nationalId: {
                label: 'National Identification Number',
                placeholder: 'Enter 10-character ID number'
            }
        },
        tajikistan: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        tanzania: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        thailand: {
            medicalLicense: {
                label: 'Medical Council Registration Number',
                placeholder: 'Enter registration number'
            },
            nationalId: {
                label: 'Thai ID Number',
                placeholder: 'Enter 13-digit Thai ID number'
            }
        },
        'timor-leste': {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        togo: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        tonga: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        'trinidad and tobago': {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Card Number',
                placeholder: 'Enter ID card number'
            }
        },
        tunisia: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        turkey: {
            medicalLicense: {
                label: 'TTB Registration Number',
                placeholder: 'Enter TTB registration number'
            },
            nationalId: {
                label: 'Turkish ID Number',
                placeholder: 'Enter 11-digit ID number'
            }
        },
        turkmenistan: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Personal ID Number',
                placeholder: 'Enter personal ID number'
            }
        },
        tuvalu: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        uganda: {
            medicalLicense: {
                label: 'Uganda Medical and Dental Practitioners Council Number',
                placeholder: 'Enter UMDPC registration number'
            },
            nationalId: {
                label: 'NIN',
                placeholder: 'Enter 14-digit National Identification Number'
            }
        },
        ukraine: {
            medicalLicense: {
                label: 'Medical Practitioner Registration Number',
                placeholder: 'Enter registration number'
            },
            nationalId: {
                label: 'Taxpayer Identification Number',
                placeholder: 'Enter TIN (10 digits)'
            }
        },
        'united arab emirates': {
            medicalLicense: {
                label: 'DHA/MOH License Number',
                placeholder: 'Enter DHA or MOH license number'
            },
            nationalId: {
                label: 'Emirates ID',
                placeholder: 'Enter 15-digit Emirates ID'
            }
        },
        'united kingdom': {
            medicalLicense: {
                label: 'GMC Registration Number',
                placeholder: 'Enter GMC registration number'
            },
            nationalId: {
                label: 'National Insurance Number',
                placeholder: 'Enter NI number (e.g., QQ123456C)'
            }
        },
        'united states of america': {
            medicalLicense: {
                label: 'State Medical License',
                placeholder: 'Enter state medical license number'
            },
            nationalId: {
                label: 'Social Security Number',
                placeholder: 'Enter SSN (without dashes)'
            }
        },
        uruguay: {
            medicalLicense: {
                label: 'Medical Practitioner License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'Cédula de Identidad',
                placeholder: 'Enter ID number'
            }
        },
        uzbekistan: {
            medicalLicense: {
                label: 'Medical Registration Number',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'Passport Number',
                placeholder: 'Enter passport number'
            }
        },
        vanuatu: {
            medicalLicense: {
                label: 'Medical Council License',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        'vatican city': {
            medicalLicense: {
                label: 'Holy See Medical Registration',
                placeholder: 'Enter medical registration number'
            },
            nationalId: {
                label: 'Personal ID Number',
                placeholder: 'Enter personal ID number'
            }
        },
        venezuela: {
            medicalLicense: {
                label: 'Medical College Registration Number',
                placeholder: 'Enter registration number'
            },
            nationalId: {
                label: 'Cédula de Identidad',
                placeholder: 'Enter ID number (e.g., V-12345678)'
            }
        },
        vietnam: {
            medicalLicense: {
                label: 'Medical Practice Certificate Number',
                placeholder: 'Enter certificate number'
            },
            nationalId: {
                label: 'Citizen Identification Number',
                placeholder: 'Enter 12-digit ID number'
            }
        },
        yemen: {
            medicalLicense: {
                label: 'Medical License Number',
                placeholder: 'Enter medical license number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        },
        zambia: {
            medicalLicense: {
                label: 'Health Professions Council of Zambia Number',
                placeholder: 'Enter HPCZ registration number'
            },
            nationalId: {
                label: 'National Registration Card Number',
                placeholder: 'Enter NRC number'
            }
        },
        zimbabwe: {
            medicalLicense: {
                label: 'Medical and Dental Practitioners Council Number',
                placeholder: 'Enter MDPCZ registration number'
            },
            nationalId: {
                label: 'National ID Number',
                placeholder: 'Enter national ID number'
            }
        }
    };

    countrySelect.addEventListener('change', function() {
        const selectedCountry = this.value;
        if (selectedCountry && countryFields[selectedCountry]) {
            const fields = countryFields[selectedCountry];
            
            // Update medical license field
            medicalLicenseGroup.querySelector('label').textContent = fields.medicalLicense.label;
            medicalLicenseInput.placeholder = fields.medicalLicense.placeholder;
            
            // Update national ID field
            nationalIdGroup.querySelector('label').textContent = fields.nationalId.label;
            nationalIdInput.placeholder = fields.nationalId.placeholder;
            
            // Show fields
            medicalLicenseGroup.style.display = 'block';
            nationalIdGroup.style.display = 'block';
        } else {
            // Hide fields if no country is selected
            medicalLicenseGroup.style.display = 'none';
            nationalIdGroup.style.display = 'none';
        }
    });

    // Add event listener for pro-country
    proCountrySelect.addEventListener('change', function() {
        const selectedCountry = this.value;
        const proCNICInput = document.getElementById('pro-cnic');
        
        if (selectedCountry === 'pakistan') {
            proCNICGroup.style.display = 'block';
            proCNICInput.required = true;
            proCNICInput.placeholder = 'Enter without dashes (e.g., 3520212345678)';
            proCNICInput.previousElementSibling.textContent = 'CNIC Number';
        } else {
            proCNICGroup.style.display = 'block';
            proCNICInput.required = true;
            proCNICInput.placeholder = 'Enter national ID number';
            proCNICInput.previousElementSibling.textContent = 'National ID Number';
        }
    });

    // File size validation - updated to 5MB limit
    [imageInput, resumeInput, proImageInput, proResumeInput].forEach(input => {
        if (input) {
            input.addEventListener('change', function() {
                if (!this.files || !this.files[0]) return;
                
                const fileSize = this.files[0].size;
                const maxSize = 5 * 1024 * 1024; // 5MB
                
                if (fileSize > maxSize) {
                    alert('File size exceeds 5MB limit. Please choose a smaller file.');
                    this.value = '';
                }
            });
        }
    });

    // Specialty change handler
    specialtySelect.addEventListener('change', function() {
        const selectedSpecialty = specialtySelect.value;
        
        // Handle sub-specialty sections
        fcpsSubSpecialty.style.display = selectedSpecialty === 'FCPS Consultant' ? 'block' : 'none';
        alliedHealthSubSpecialty.style.display = selectedSpecialty === 'Allied Health Services Professional' ? 'block' : 'none';
    });

    // Doctor form submission handler
    doctorForm.addEventListener('submit', function(e) {
        e.preventDefault();

        // Validate required fields
        const requiredFields = doctorForm.querySelectorAll('[required]');
        for (let field of requiredFields) {
            if (!field.value) {
                alert('Please fill in all required fields.');
                field.focus();
                return;
            }
        }

        // Show loading spinner
        loadingSpinner.style.display = 'flex';

        const formData = new FormData(doctorForm);

        // Remove PMDC number for Allied Health
        if (specialtySelect.value === 'Allied Health Services Professional') {
            formData.delete('pmdc-number');
        }

        // Add timestamp
        formData.append('timestamp', new Date().toISOString());

        fetch('/register-doctor', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            loadingSpinner.style.display = 'none';
            if (data.success) {
                alert('Doctor registered successfully.');
                doctorForm.reset();
                // Reset specialty sections
                fcpsSubSpecialty.style.display = 'none';
                alliedHealthSubSpecialty.style.display = 'none';
            } else {
                alert(data.message || 'Failed to register doctor.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred. Please try again.');
            loadingSpinner.style.display = 'none';
        });
    });

    // Professional form submission handler
    if (professionalForm) {
        professionalForm.addEventListener('submit', function(e) {
            e.preventDefault();

            // Validate required fields
            const requiredFields = professionalForm.querySelectorAll('[required]');
            for (let field of requiredFields) {
                if (!field.value) {
                    alert('Please fill in all required fields.');
                    field.focus();
                    return;
                }
            }

            // Show loading spinner
            loadingSpinner.style.display = 'flex';

            const formData = new FormData(professionalForm);

            // Add timestamp
            formData.append('timestamp', new Date().toISOString());

            fetch('/register-professional', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                loadingSpinner.style.display = 'none';
                if (data.success) {
                    alert('Registration successful.');
                    professionalForm.reset();
                } else {
                    alert(data.message || 'Failed to complete registration.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
                loadingSpinner.style.display = 'none';
            });
        });
    }
});
