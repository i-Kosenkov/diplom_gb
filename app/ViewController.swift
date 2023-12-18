import UIKit

class ViewController: UIViewController {
    
    @IBOutlet weak var textView: UITextView!
    
    override func viewDidLoad() {

        super.viewDidLoad()
        readFromFile()
    }
    
    func readFromFile(){
        if let path = Bundle.main.path(forResource:  "log", ofType: "log"){
            let text = try? String(contentsOfFile: path)
            textView.text = text
        }
    }
}

