import React from 'react';
import './Dialog.css';

const Dialog: React.FC = () => {
  return (
    <div className="truth-seeker-dialog">
      <div className="dialog-header">
        <div className="dialog-title">
          TruthSeeker
          <img src="/ai-icon.png" alt="AI Icon" className="ai-icon" />
        </div>
      </div>
      <div className="dialog-body">
        <strong>
          Claim: &quot;we lost 800K jobs monthly, had a $1.4T deficit, and the financial system was near collapse? Now we&apos;re better.&quot;
        </strong>
        <p>
          This oversimplifies the turnaround by attributing it solely to Obama’s policies,
          ignoring other factors (a false cause fallacy).
        </p>
      </div>
    </div>
  );
};

export default Dialog;
