import './App.css';
import React, { useState, useEffect } from "react";
import axios from 'axios';

function App() {
  const [inputText, setInputText] = useState("");
  const [responseMessage, setResponseMessage] = useState("");
  const [curStatus, setCurStatus] = useState("Upload");

  const backend_url_1 = process.env.REACT_APP_UPLOAD_BACKEND_URL;
  const backend_url_2 = process.env.REACT_APP_REQUEST_BACKEND_URL;

  useEffect(() => {
    if(curStatus.startsWith("Deploying")){
      const interval = setInterval(async () => {
          const response = await axios.get(`${backend_url_2}/status/?id=bucket${responseMessage}`);
          if(response.data.msg==="deployed") setCurStatus("Deployed"); 
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [curStatus, backend_url_2, responseMessage]);

  const handleInputChange = (e) => {
    setInputText(e.target.value);
  }
  async function handleUpload() {
    // check the inputText is valid github url or not
    if(!inputText.includes('https://github.com')){
      setResponseMessage('Invalid Github URL');
      return;
    }
    
    const data = {
      github_url : inputText
    }
    console.log(data)
    setCurStatus("uploading");
    try{
      const response = await axios.post(`${backend_url_1}/collect_files`, data);

      if(response.data.unique_id) setResponseMessage(`${response.data.unique_id}`);
      if(response.data.unique_id) setCurStatus(`Deploying..(${response.data.unique_id})`);

    }catch(error){
      setResponseMessage('Error Occured');
    }

    // if curStatus is not deployed then display none second-one class
    
  } 
  // if(curStatus !== "Deployed") document.querySelector('.second-one').style.display = 'none';
  return (
    <div className="main">
      <div className="main-head">
        <h2 className='heading'> Deploy your application</h2>
        <input placeholder='Paste Github Repository Url'  name="myInput" className='text-box' value={inputText} onChange={handleInputChange}/>
        <button className='button' onClick={handleUpload}>
          {curStatus}
        </button>
      </div>
      {curStatus === "Deployed" && (
        <div className="main-head second-one">
          <h2 className='heading'> Deployed Url</h2>
          <div className='responsive-paragraph'>
            {`http://${responseMessage}.myvercel.com:8000/index.html`}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
