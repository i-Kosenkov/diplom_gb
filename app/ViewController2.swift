import UIKit

class ViewController2: UIViewController {
    
    @IBOutlet weak var buttonMakeOrders: UIButton!
    @IBOutlet weak var buttonOrders: UIButton!
    @IBOutlet weak var buttonReturns: UIButton!
    @IBOutlet weak var buttonStock: UIButton!
    
    var timer: Timer?
    var progress: Float = 0

    @IBOutlet weak var activityIndicator: UIActivityIndicatorView!
    @IBAction func button4(_ sender: UIButton) {
        progress = 0
        buttonMakeOrders.tintColor = UIColor.green
        timer = Timer.scheduledTimer(timeInterval: 0.5, target: self, selector: #selector(ViewController2.but4), userInfo: nil, repeats: true)
        timer?.fire()
        activityIndicator.startAnimating()
    }
    
    @IBAction func button3(_ sender: UIButton) {
        progress = 0
        buttonOrders.tintColor = UIColor.green
        timer = Timer.scheduledTimer(timeInterval: 0.5, target: self, selector: #selector(ViewController2.but3), userInfo: nil, repeats: true)
        timer?.fire()
        activityIndicator.startAnimating()
    }
    
    @IBAction func button2(_ sender: UIButton) {
        progress = 0
        buttonReturns.tintColor = UIColor.green
        timer = Timer.scheduledTimer(timeInterval: 0.5, target: self, selector: #selector(ViewController2.but2), userInfo: nil, repeats: true)
        timer?.fire()
        activityIndicator.startAnimating()
    }
    
    @IBAction func button1(_ sender: AnyObject) {
        progress = 0
        buttonStock.tintColor = UIColor.green
        timer = Timer.scheduledTimer(timeInterval: 0.5, target: self, selector: #selector(ViewController2.but1), userInfo: nil, repeats: true)
        timer?.fire()
        activityIndicator.startAnimating()
    }
    
    @objc func but1(){
        progress += 0.2
        if progress >= 1{
            timer?.invalidate()
            readStockFile()
            activityIndicator.stopAnimating()
            buttonStock.tintColor = UIColor.link
        }
    }
    
    @objc func but2(){
        progress += 0.2
        if progress >= 1{
            timer?.invalidate()
            readReturnsFile()
            activityIndicator.stopAnimating()
            buttonReturns.tintColor = UIColor.link
        }
    }
    
    @objc func but3(){
        progress += 0.2
        if progress >= 1{
            timer?.invalidate()
            readOrderFile()
            activityIndicator.stopAnimating()
            buttonOrders.tintColor = UIColor.link
        }
    }
    
    @objc func but4(){
        progress += 0.2
        if progress >= 1{
            timer?.invalidate()
            activityIndicator.stopAnimating()
            textView.text = "Нет заказов для сборки"
            buttonMakeOrders.tintColor = UIColor.link
        }
    }
    
    
    @IBOutlet weak var textView: UITextView!
    override func viewDidLoad() {
        super.viewDidLoad()
    }
    
    func readStockFile(){
        if let path = Bundle.main.path(forResource:  "stock", ofType: "log"){
            let text = try? String(contentsOfFile: path)
            textView.text = text
        }
    }
    
    func readReturnsFile(){
        if let path = Bundle.main.path(forResource:  "returns", ofType: "log"){
            let text = try? String(contentsOfFile: path)
            textView.text = text
        }
    }
    
    func readOrderFile(){
        if let path = Bundle.main.path(forResource:  "order", ofType: "log"){
            let text = try? String(contentsOfFile: path)
            textView.text = text
        }
    }
    

    /*
    // MARK: - Navigation

    // In a storyboard-based application, you will often want to do a little preparation before navigation
    override func prepare(for segue: UIStoryboardSegue, sender: Any?) {
        // Get the new view controller using segue.destination.
        // Pass the selected object to the new view controller.
    }
    */

}
